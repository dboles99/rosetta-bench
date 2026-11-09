from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal

_MODES = {"even": ROUND_HALF_EVEN, "up": ROUND_HALF_UP}


def round_price(amount, mode="even"):
    if mode not in _MODES:
        raise ValueError(f"unknown mode {mode!r}")
    value = Decimal(str(amount))
    if value < 0:
        raise ValueError("amount must not be negative")
    return int(value.quantize(Decimal(1), rounding=_MODES[mode]))
