import math

def nearest_rank_percentile(values, q):
    ordered = sorted(values)
    if not ordered:
        return None
    rank = max(1, math.ceil(q * len(ordered)))
    return ordered[min(rank, len(ordered)) - 1]
