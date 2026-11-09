import re

_AMOUNT = re.compile(r"([0-9]+)\.([0-9]{2})")


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def allocate(total_cents, ratios):
    if not _is_int(total_cents) or total_cents < 0:
        raise ValueError("total_cents must be a non-negative integer")
    ratios = list(ratios)
    if not ratios:
        raise ValueError("ratios must not be empty")
    if any(not _is_int(r) or r < 0 for r in ratios):
        raise ValueError("ratios must be non-negative integers")
    total_ratio = sum(ratios)
    if total_ratio == 0:
        raise ValueError("ratios must not sum to zero")
    shares = [total_cents * r // total_ratio for r in ratios]
    remainders = [total_cents * r % total_ratio for r in ratios]
    left = total_cents - sum(shares)
    order = sorted((i for i in range(len(ratios)) if ratios[i] > 0),
                   key=lambda i: (-remainders[i], -ratios[i], i))
    for i in order[:left]:
        shares[i] += 1
    return shares


def allocate_amount(amount, ratios):
    match = _AMOUNT.fullmatch(amount) if isinstance(amount, str) else None
    if match is None:
        raise ValueError(f"invalid amount: {amount!r}")
    cents = int(match.group(1)) * 100 + int(match.group(2))
    return [f"{c // 100}.{c % 100:02d}" for c in allocate(cents, ratios)]
