def _clean(intervals):
    out = []
    for start, end in intervals:
        if start > end:
            raise ValueError(f"interval start > end: {(start, end)}")
        if start < end:
            out.append((start, end))
    return out


def merge(intervals):
    merged = []
    for start, end in sorted(_clean(intervals)):
        if merged and start <= merged[-1][1]:
            if end > merged[-1][1]:
                merged[-1] = (merged[-1][0], end)
        else:
            merged.append((start, end))
    return merged


def subtract(a, b):
    cuts = merge(b)
    result = []
    for start, end in merge(a):
        current = start
        for cut_start, cut_end in cuts:
            if cut_end <= current or cut_start >= end:
                continue
            if cut_start > current:
                result.append((current, cut_start))
            current = max(current, cut_end)
            if current >= end:
                break
        if current < end:
            result.append((current, end))
    return result


def total_length(intervals):
    return sum(end - start for start, end in merge(intervals))
