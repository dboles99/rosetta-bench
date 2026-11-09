import heapq
from collections import Counter


def _check(x):
    if isinstance(x, bool) or not isinstance(x, int):
        raise TypeError("values must be int")


class MedianTracker:
    def __init__(self, prefer_high=False):
        self.prefer_high = prefer_high
        self._low = []  # max-heap via negatives
        self._high = []  # min-heap
        self._low_size = 0
        self._high_size = 0
        self._delayed = Counter()
        self._count = Counter()

    def _prune(self, heap, sign):
        while heap and self._delayed[sign * heap[0]]:
            value = sign * heapq.heappop(heap)
            self._delayed[value] -= 1

    def _rebalance(self):
        if self._low_size > self._high_size + 1:
            heapq.heappush(self._high, -heapq.heappop(self._low))
            self._low_size -= 1
            self._high_size += 1
            self._prune(self._low, -1)
        elif self._low_size < self._high_size:
            heapq.heappush(self._low, -heapq.heappop(self._high))
            self._high_size -= 1
            self._low_size += 1
            self._prune(self._high, 1)

    def add(self, x):
        _check(x)
        self._count[x] += 1
        if not self._low or x <= -self._low[0]:
            heapq.heappush(self._low, -x)
            self._low_size += 1
        else:
            heapq.heappush(self._high, x)
            self._high_size += 1
        self._rebalance()

    def remove(self, x):
        _check(x)
        if not self._count[x]:
            raise ValueError(f"not present: {x}")
        self._count[x] -= 1
        self._delayed[x] += 1
        if x <= -self._low[0]:
            self._low_size -= 1
            if x == -self._low[0]:
                self._prune(self._low, -1)
        else:
            self._high_size -= 1
            if x == self._high[0]:
                self._prune(self._high, 1)
        self._rebalance()

    def median(self):
        total = self._low_size + self._high_size
        if total == 0:
            raise LookupError("empty")
        if total % 2 == 0 and self.prefer_high:
            return self._high[0]
        return -self._low[0]

    def __len__(self):
        return self._low_size + self._high_size
