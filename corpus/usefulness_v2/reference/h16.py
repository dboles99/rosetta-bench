def _invalid(detail):
    return ValueError(f"invalid cron field: {detail}")


def _number(text, lo, hi):
    if not (text.isascii() and text.isdigit()):
        raise _invalid(text)
    value = int(text)
    if not lo <= value <= hi:
        raise _invalid(f"{value} outside {lo}-{hi}")
    return value


def expand_field(field, lo, hi):
    if not isinstance(field, str) or field == "":
        raise _invalid("empty field")
    values = set()
    for item in field.split(","):
        if item == "":
            raise _invalid("empty item")
        base, has_step, step_text = item.partition("/")
        if has_step:
            if not (step_text.isascii() and step_text.isdigit()) or int(step_text) == 0:
                raise _invalid(f"bad step in {item}")
            step = int(step_text)
        else:
            step = 1
        if base == "*":
            start, end = lo, hi
        elif "-" in base:
            first, _, last = base.partition("-")
            start, end = _number(first, lo, hi), _number(last, lo, hi)
            if start > end:
                raise _invalid(f"reversed range {item}")
        else:
            start = _number(base, lo, hi)
            end = hi if has_step else start
        values.update(range(start, end + 1, step))
    return sorted(values)


def _parse(expr):
    if not isinstance(expr, str):
        raise ValueError("invalid cron expression")
    parts = expr.split()
    if len(parts) != 2:
        raise ValueError("invalid cron expression: expected two fields")
    return set(expand_field(parts[0], 0, 59)), set(expand_field(parts[1], 0, 23))


def cron_matches(expr, hour, minute):
    minutes, hours = _parse(expr)
    return minute in minutes and hour in hours


def next_match(expr, hour, minute):
    minutes, hours = _parse(expr)
    start = hour * 60 + minute
    for offset in range(1, 24 * 60 + 1):
        h, m = divmod((start + offset) % (24 * 60), 60)
        if h in hours and m in minutes:
            return (h, m)
    raise AssertionError("unreachable: every valid field matches something")
