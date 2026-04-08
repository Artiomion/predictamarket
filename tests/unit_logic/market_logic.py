"""Extracted market business logic."""


def escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


PERIOD_MAP = {"1m": 30, "3m": 90, "6m": 180, "1y": 365, "2y": 730, "5y": 1825, "max": 9999}


def period_to_days(period: str) -> int:
    return PERIOD_MAP.get(period, 365)
