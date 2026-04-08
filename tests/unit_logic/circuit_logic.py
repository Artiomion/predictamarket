"""Circuit breaker logic — mirrors shared/yfinance_utils.py for unit testing."""

import time


class CircuitBreaker:
    def __init__(self, threshold: int = 5, cooldown: float = 60) -> None:
        self.threshold = threshold
        self.cooldown = cooldown
        self.failures = 0
        self._open_until: float = 0

    @property
    def is_open(self) -> bool:
        if self.failures >= self.threshold:
            if time.monotonic() < self._open_until:
                return True
            # Cooldown passed
            return False
        return False

    def record_failure(self) -> None:
        self.failures += 1
        if self.failures >= self.threshold:
            self._open_until = time.monotonic() + self.cooldown

    def record_success(self) -> None:
        self.failures = 0
