"""Extracted forecast business logic."""


def determine_signal(median_1d: float, current_close: float) -> str:
    if abs(median_1d - current_close) / current_close < 0.005:
        return "HOLD"
    return "BUY" if median_1d > current_close else "SELL"


def determine_confidence(lower_80: float, upper_80: float, median: float, current: float) -> str:
    if lower_80 > current:
        return "HIGH"
    if upper_80 < current:
        return "HIGH"
    return "MEDIUM"
