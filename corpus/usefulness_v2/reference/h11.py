_DIGITS = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_CHECK = _DIGITS + "*~$=U"
_ALIASES = {"I": "1", "L": "1", "O": "0"}


def encode_id(n):
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError("n must be an int")
    if n < 0:
        raise ValueError("n must be non-negative")
    digits = []
    value = n
    while True:
        value, rem = divmod(value, 32)
        digits.append(_DIGITS[rem])
        if value == 0:
            break
    return "".join(reversed(digits)) + _CHECK[n % 37]


def decode_id(s):
    cleaned = [_ALIASES.get(ch, ch) for ch in s.replace("-", "").upper()]
    if len(cleaned) < 2:
        raise ValueError("too short")
    *body, check = cleaned
    value = 0
    for ch in body:
        index = _DIGITS.find(ch)
        if index < 0:
            raise ValueError(f"invalid symbol {ch!r}")
        value = value * 32 + index
    if check not in _CHECK:
        raise ValueError(f"invalid check symbol {check!r}")
    if _CHECK.index(check) != value % 37:
        raise ValueError("checksum mismatch")
    return value
