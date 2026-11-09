def clamp(x, lo, hi):
    if lo > hi:
        raise ValueError("lo must not exceed hi")
    return max(lo, min(x, hi))
