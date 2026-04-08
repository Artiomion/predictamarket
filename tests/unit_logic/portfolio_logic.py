"""Extracted portfolio business logic."""


def weighted_avg(old_qty: float, old_avg: float, new_qty: float, new_price: float) -> float:
    total = old_qty + new_qty
    return (old_qty * old_avg + new_qty * new_price) / total


def sanitize_csv(val: str) -> str:
    if val and val[0] in ("=", "+", "-", "@", "\t", "\r"):
        return f"'{val}"
    return val


def clamp_sell(held: float, requested: float | None) -> float:
    return min(requested or held, held)
