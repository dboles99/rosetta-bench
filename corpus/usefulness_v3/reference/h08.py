import math
from collections import deque


def _validate(values, limit):
    if isinstance(limit, bool) or not isinstance(limit, (int, float)) or limit != limit or limit < 0:
        raise ValueError("limit must be a number >= 0")
    for v in values:
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise TypeError("values must be int or float")
        if isinstance(v, float) and math.isnan(v):
            raise ValueError("nan in values")


def _scan(values, limit):
    """Yield (left, right) for every right: the smallest left with max - min <= limit."""
    maxq, minq = deque(), deque()
    left = 0
    for right, v in enumerate(values):
        while maxq and values[maxq[-1]] <= v:
            maxq.pop()
        maxq.append(right)
        while minq and values[minq[-1]] >= v:
            minq.pop()
        minq.append(right)
        while values[maxq[0]] - values[minq[0]] > limit:
            left += 1
            if maxq[0] < left:
                maxq.popleft()
            if minq[0] < left:
                minq.popleft()
        yield left, right


def longest_calm(values, limit):
    _validate(values, limit)
    best = (0, 0)
    for left, right in _scan(values, limit):
        if right + 1 - left > best[1] - best[0]:
            best = (left, right + 1)
    return best


def count_calm(values, limit):
    _validate(values, limit)
    return sum(right + 1 - left for left, right in _scan(values, limit))
