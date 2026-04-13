"""Billing endpoints — Stripe checkout, portal, subscription management."""

import uuid

import stripe
import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
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

    customer = stripe.Customer.create(
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

    checkout_session = stripe.checkout.Session.create(
        customer=customer_id,
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url="http://localhost:3000/billing/success?session_id={CHECKOUT_SESSION_ID}",
        cancel_url="http://localhost:3000/billing/cancel",
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

    portal_session = stripe.billing_portal.Session.create(
        customer=user.stripe_customer_id,
        return_url="http://localhost:3000/settings",
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

    subscriptions = stripe.Subscription.list(
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
