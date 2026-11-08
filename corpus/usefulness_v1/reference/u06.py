import math

def validate_distribution(probs, tol=0.02):
    if not probs:
        return False
    for value in probs.values():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
            return False
    return abs(sum(probs.values()) - 1) <= tol
