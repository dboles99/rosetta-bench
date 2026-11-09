_OPS = ("==", "!=", ">=", "<=", "~=", ">", "<")


def _parse_version(text):
    parts = text.strip().split(".")
    if not text.strip() or any(not p.isascii() or not p.isdigit() for p in parts):
        raise ValueError(f"invalid version: {text!r}")
    return tuple(int(p) for p in parts)


def _cmp(a, b):
    width = max(len(a), len(b))
    a = a + (0,) * (width - len(a))
    b = b + (0,) * (width - len(b))
    return (a > b) - (a < b)


def _clauses(spec):
    if not spec.strip():
        return []
    clauses = []
    for raw in spec.split(","):
        clause = raw.strip()
        for op in _OPS:
            if clause.startswith(op):
                version = _parse_version(clause[len(op):])
                if op == "~=" and len(version) < 2:
                    raise ValueError("~= needs at least two components")
                clauses.append((op, version))
                break
        else:
            raise ValueError(f"clause without operator: {clause!r}")
    return clauses


def _holds(version, op, target):
    c = _cmp(version, target)
    if op == "==":
        return c == 0
    if op == "!=":
        return c != 0
    if op == ">=":
        return c >= 0
    if op == "<=":
        return c <= 0
    if op == ">":
        return c > 0
    if op == "<":
        return c < 0
    upper = target[:-2] + (target[-2] + 1,)
    return c >= 0 and _cmp(version, upper) < 0


def satisfies(version, spec):
    parsed = _parse_version(version)
    return all(_holds(parsed, op, target) for op, target in _clauses(spec))


def max_satisfying(versions, spec):
    clauses = _clauses(spec)
    best = None
    best_parsed = None
    for text in versions:
        parsed = _parse_version(text)
        if all(_holds(parsed, op, target) for op, target in clauses):
            if best is None or _cmp(parsed, best_parsed) > 0:
                best, best_parsed = text, parsed
    return best
