def parse_retry_after(value, default, cap):
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        seconds = float(default)
    return float(min(max(seconds, 0.0), cap))
