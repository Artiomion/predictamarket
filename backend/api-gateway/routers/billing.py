"""Billing endpoints — Stripe checkout, portal, subscription, webhook."""

import asyncio
import uuid

import httpx
import stripe
import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from shared.config import settings
from shared.database import get_session
from shared.models.auth import User

logger = structlog.get_logger()
router = APIRouter()

stripe.api_key = settings.STRIPE_SECRET_KEY

# ── Static plan definitions ──────────────────────────────────────────────────

PLANS = [
    {
        "id": "free",
        "name": "Free",
        "price_monthly": 0,
        "price_annual": 0,
        "features": [
            "1 forecast/day",
            "Top 5 picks",
            "1 portfolio",
            "Basic charts",
        ],
        "limits": {"forecasts_per_day": 1, "top_picks": 5, "portfolios": 1},
    },
    {
        "id": "pro",
        "name": "Pro",
        "price_monthly": 15,
        "price_annual": 150,
        "popular": True,
        "features": [
            "10 forecasts/day",
            "Top 20 picks",
            "5 portfolios",
            "SEC EDGAR",
            "All indicators",
            "Sentiment trends",
            "Push alerts",
        ],
        "limits": {"forecasts_per_day": 10, "top_picks": 20, "portfolios": 5},
    },
    {
        "id": "premium",
        "name": "Premium",
        "price_monthly": 39,
        "price_annual": 390,
        "features": [
            "Unlimited forecasts",
            "All Pro features",
            "API access",
            "Backtesting",
            "CSV/PDF export",
            "Priority inference",
        ],
        "limits": {"forecasts_per_day": -1, "top_picks": 50, "portfolios": 10},
    },
]

PRICE_MAP: dict[str, str] = {
    "pro_monthly": settings.STRIPE_PRICE_PRO_MONTHLY,
    "pro_annual": settings.STRIPE_PRICE_PRO_ANNUAL,
    "premium_monthly": settings.STRIPE_PRICE_PREMIUM_MONTHLY,
    "premium_annual": settings.STRIPE_PRICE_PREMIUM_ANNUAL,
}

# ── Helpers ──────────────────────────────────────────────────────────────────


def _require_user(request: Request) -> tuple[uuid.UUID, str]:
    """Extract user_id and tier from JWT middleware state."""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    tier = getattr(request.state, "user_tier", "free")
    return uuid.UUID(user_id), tier


async def _get_or_create_stripe_customer(
    session: AsyncSession, user_id: uuid.UUID,
) -> str:
    """Get existing Stripe customer ID or create one."""
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.stripe_customer_id:
        return user.stripe_customer_id

    customer = await asyncio.to_thread(
        stripe.Customer.create,
        email=user.email,
        name=user.full_name,
        metadata={"user_id": str(user_id)},
    )

    await session.execute(
        update(User)
        .where(User.id == user_id)
        .values(stripe_customer_id=customer.id)
    )
    await session.commit()
    await logger.ainfo("stripe_customer_created", user_id=str(user_id), customer_id=customer.id)
    return customer.id


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.get("/plans")
async def get_plans():
    """Return available subscription plans (public, no auth)."""
    return PLANS


class CheckoutRequest(BaseModel):
    plan: str  # "pro" | "premium"
    billing: str = "monthly"  # "monthly" | "annual"


@router.post("/checkout")
async def create_checkout(
    body: CheckoutRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Create a Stripe Checkout Session for subscription."""
    user_id, _ = _require_user(request)

    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Billing is not configured")

    price_key = f"{body.plan}_{body.billing}"
    price_id = PRICE_MAP.get(price_key)
    if not price_id:
        raise HTTPException(status_code=400, detail=f"Invalid plan/billing: {body.plan}/{body.billing}")

    customer_id = await _get_or_create_stripe_customer(session, user_id)

    checkout_session = await asyncio.to_thread(
        stripe.checkout.Session.create,
        customer=customer_id,
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url=f"{settings.FRONTEND_URL}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{settings.FRONTEND_URL}/billing/cancel",
        metadata={"user_id": str(user_id), "plan": body.plan},
    )

    await logger.ainfo("checkout_session_created", user_id=str(user_id), plan=body.plan)
    return {"checkout_url": checkout_session.url}


@router.get("/portal")
async def get_billing_portal(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Create a Stripe Billing Portal session for managing subscription."""
    user_id, _ = _require_user(request)

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No active subscription")

    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Billing is not configured")

    portal_session = await asyncio.to_thread(
        stripe.billing_portal.Session.create,
        customer=user.stripe_customer_id,
        return_url=f"{settings.FRONTEND_URL}/settings",
    )

    return {"portal_url": portal_session.url}


@router.get("/subscription")
async def get_subscription(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Get current user's subscription status."""
    user_id, tier = _require_user(request)

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.stripe_customer_id:
        return {"plan": tier, "status": None}

    if not settings.STRIPE_SECRET_KEY:
        return {"plan": tier, "status": None}

    subscriptions = await asyncio.to_thread(
        stripe.Subscription.list,
        customer=user.stripe_customer_id, limit=1, status="active",
    )

    if not subscriptions.data:
        return {"plan": tier, "status": None}

    sub = subscriptions.data[0]
    return {
        "plan": tier,
        "status": sub.status,
        "current_period_end": sub.current_period_end,
        "cancel_at_period_end": sub.cancel_at_period_end,
    }


# ── Webhook ──────────────────────────────────────────────────────────────────

def _price_to_plan(price_id: str) -> str:
    """Map Stripe price_id to plan name."""
    mapping = {
        settings.STRIPE_PRICE_PRO_MONTHLY: "pro",
        settings.STRIPE_PRICE_PRO_ANNUAL: "pro",
        settings.STRIPE_PRICE_PREMIUM_MONTHLY: "premium",
        settings.STRIPE_PRICE_PREMIUM_ANNUAL: "premium",
    }
    return mapping.get(price_id, "free")


async def _update_user_tier(user_id: str, plan: str) -> None:
    """Call auth-service internal endpoint to update user tier.

    Raises on failure so the webhook returns non-200 and Stripe retries.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.put(
            f"{settings.AUTH_SERVICE_URL}/api/auth/tier",
            json={"user_id": user_id, "tier": plan},
            headers={"x-internal-key": settings.INTERNAL_API_KEY},
        )
        if resp.status_code != 200:
            await logger.aerror(
                "tier_update_failed",
                user_id=user_id, plan=plan,
                status=resp.status_code, body=resp.text,
            )
            raise RuntimeError(f"tier update failed: {resp.status_code}")


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events. Signature verification required."""
    payload = await request.body()
    sig = request.headers.get("stripe-signature")

    if not sig:
        return JSONResponse(status_code=400, content={"detail": "Missing stripe-signature header"})

    if not settings.STRIPE_WEBHOOK_SECRET:
        await logger.aerror("webhook_secret_not_configured")
        return JSONResponse(status_code=500, content={"detail": "Webhook secret not configured"})

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig,
            secret=settings.STRIPE_WEBHOOK_SECRET,
        )
    except stripe.error.SignatureVerificationError:
        await logger.awarning("webhook_signature_invalid")
        return JSONResponse(status_code=400, content={"detail": "Invalid signature"})
    except ValueError:
        return JSONResponse(status_code=400, content={"detail": "Invalid payload"})

    event_type = event["type"]
    data = event["data"]["object"]

    await logger.ainfo("stripe_webhook_received", event_type=event_type, event_id=event["id"])

    # ── checkout.session.completed ────────────────────────────────────────
    if event_type == "checkout.session.completed":
        user_id = data.get("metadata", {}).get("user_id")
        plan = data.get("metadata", {}).get("plan")
        subscription_id = data.get("subscription")

        if user_id and plan:
            try:
                await _update_user_tier(user_id, plan)
            except Exception:
                await logger.aexception("checkout_tier_update_failed", user_id=user_id, plan=plan)
                return JSONResponse(status_code=500, content={"detail": "Tier update failed, will retry"})

            await logger.ainfo("tier_upgraded", user_id=user_id, plan=plan, subscription_id=subscription_id)

            if subscription_id:
                try:
                    async for session in get_session():
                        await session.execute(
                            update(User)
                            .where(User.id == uuid.UUID(user_id))
                            .values(stripe_subscription_id=subscription_id)
                        )
                        await session.commit()
                        break
                except Exception:
                    await logger.aexception("save_subscription_id_failed", user_id=user_id)

    # ── customer.subscription.updated ────────────────────────────────────
    elif event_type == "customer.subscription.updated":
        customer_id = data.get("customer")
        status = data.get("status")
        items = data.get("items", {}).get("data", [])

        if items and status == "active":
            price_id = items[0].get("price", {}).get("id")
            new_plan = _price_to_plan(price_id)

            # Find user by stripe_customer_id
            try:
                async for session in get_session():
                    result = await session.execute(
                        select(User).where(User.stripe_customer_id == customer_id)
                    )
                    user = result.scalar_one_or_none()
                    if user and user.tier != new_plan:
                        await _update_user_tier(str(user.id), new_plan)
                        await logger.ainfo("subscription_plan_changed", user_id=str(user.id), old=user.tier, new=new_plan)
                    break
            except Exception:
                await logger.aexception("subscription_update_failed", customer_id=customer_id)

    # ── customer.subscription.deleted ────────────────────────────────────
    elif event_type == "customer.subscription.deleted":
        customer_id = data.get("customer")

        try:
            async for session in get_session():
                result = await session.execute(
                    select(User).where(User.stripe_customer_id == customer_id)
                )
                user = result.scalar_one_or_none()
                if user:
                    await _update_user_tier(str(user.id), "free")
                    await session.execute(
                        update(User)
                        .where(User.id == user.id)
                        .values(stripe_subscription_id=None)
                    )
                    await session.commit()
                    await logger.ainfo("subscription_cancelled", user_id=str(user.id))
                break
        except Exception:
            await logger.aexception("subscription_delete_failed", customer_id=customer_id)

    # ── invoice.payment_failed ───────────────────────────────────────────
    elif event_type == "invoice.payment_failed":
        customer_id = data.get("customer")
        attempt = data.get("attempt_count", 0)

        try:
            async for session in get_session():
                result = await session.execute(
                    select(User).where(User.stripe_customer_id == customer_id)
                )
                user = result.scalar_one_or_none()
                user_id = str(user.id) if user else "unknown"
                await logger.awarning(
                    "payment_failed",
                    user_id=user_id, customer_id=customer_id, attempt=attempt,
                )
                break
        except Exception:
            await logger.aexception("payment_failed_lookup_error", customer_id=customer_id)

    return {"status": "ok"}
