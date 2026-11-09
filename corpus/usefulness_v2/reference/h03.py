_TABLE = [(1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"),
          (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]
_VALUES = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}


def to_roman(n):
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError("n must be an int")
    if not 1 <= n <= 3999:
        raise ValueError("n out of range")
    out = []
    for value, symbol in _TABLE:
        while n >= value:
            out.append(symbol)
            n -= value
    return "".join(out)


def from_roman(s):
    if not isinstance(s, str):
        raise TypeError("s must be a str")
    if not s or any(ch not in _VALUES for ch in s):
        raise ValueError(f"invalid roman numeral: {s!r}")
    total = 0
    for i, ch in enumerate(s):
        value = _VALUES[ch]
        if i + 1 < len(s) and _VALUES[s[i + 1]] > value:
            total -= value
        else:
            total += value
    if not 1 <= total <= 3999 or to_roman(total) != s:
        raise ValueError(f"invalid roman numeral: {s!r}")
    return total


def is_roman(s):
    try:
        from_roman(s)
    except (TypeError, ValueError):
        return False
    return True
