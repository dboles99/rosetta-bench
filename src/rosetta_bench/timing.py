import time
from contextlib import contextmanager
from typing import Callable, Iterator


class StageTimer:
    """Accumulates wall-clock milliseconds per named stage. A stage that raises still
    records its time, so failed calls appear in latency figures."""

    def __init__(self, clock: Callable[[], float] = time.perf_counter):
        self._clock = clock
        self.timings_ms: dict[str, float] = {}

    @contextmanager
    def stage(self, name: str) -> Iterator[None]:
        start = self._clock()
        try:
            yield
        finally:
            self.timings_ms[name] = self.timings_ms.get(name, 0.0) + (self._clock() - start) * 1000
