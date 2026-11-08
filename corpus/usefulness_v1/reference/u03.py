def brier_score(pairs):
    pairs = list(pairs)
    if not pairs:
        raise ValueError("no pairs")
    return sum((p - y) ** 2 for p, y in pairs) / len(pairs)
