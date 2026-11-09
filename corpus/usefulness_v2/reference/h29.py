def average(xs):
    total, count = 0, 0
    for x in xs:
        if isinstance(x, bool):
            raise TypeError("bool values are not averaged")
        total += x
        count += 1
    if count == 0:
        raise ValueError("empty")
    return float(total / count)
