import math


class TokenBucket:
    def __init__(self, capacity, refill_rate, clock):
        if capacity <= 0 or refill_rate < 0:
            raise ValueError("capacity must be > 0 and refill_rate >= 0")
        self.capacity = capacity
        self.refill_rate = refill_rate
        self._clock = clock
        self._tokens = float(capacity)
        self._last = clock()

    def _refill(self):
        now = self._clock()
        if now > self._last:
            self._tokens = min(float(self.capacity), self._tokens + (now - self._last) * self.refill_rate)
            self._last = now

    def _check(self, n):
        if n <= 0 or n > self.capacity:
            raise ValueError("n must be > 0 and <= capacity")

    @property
    def tokens(self):
        self._refill()
        return self._tokens

    def try_consume(self, n=1):
        self._check(n)
        self._refill()
        if self._tokens >= n:
            self._tokens -= n
            return True
        return False

    def wait_time(self, n=1):
        self._check(n)
        self._refill()
        if self._tokens >= n:
            return 0.0
        if self.refill_rate == 0:
            return math.inf
        return (n - self._tokens) / self.refill_rate
