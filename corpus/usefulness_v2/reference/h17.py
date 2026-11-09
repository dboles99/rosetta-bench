import bisect


def _validate(intervals):
    for item in intervals:
        for value in item:
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError("start, end and weight must be int")
        if item[0] >= item[1]:
            raise ValueError("start must be < end")


def best_schedule(intervals):
    _validate(intervals)
    items = sorted(intervals, key=lambda t: t[1])
    ends = [t[1] for t in items]
    best = [(0, 0)]  # (total weight, -count) over the first i intervals by end
    for i, (start, end, weight) in enumerate(items):
        j = bisect.bisect_right(ends, start, 0, i)
        take = (best[j][0] + weight, best[j][1] - 1)
        best.append(max(best[i], take))
    total, negative_count = best[-1]
    return total, -negative_count


def max_parallel(intervals):
    _validate(intervals)
    events = []
    for start, end, _ in intervals:
        events.append((start, 1))
        events.append((end, -1))
    events.sort()
    current = peak = 0
    for _, delta in events:
        current += delta
        peak = max(peak, current)
    return peak
