def _validate(prices):
    for p in prices:
        if p is None:
            continue
        if isinstance(p, bool) or not isinstance(p, (int, float)):
            raise TypeError("prices must be int, float or None")


def spans(prices):
    _validate(prices)
    out = [0] * len(prices)
    stack = []  # indices with strictly decreasing prices since the last None
    for i, p in enumerate(prices):
        if p is None:
            stack.clear()
            continue
        span = 1
        while stack and prices[stack[-1]] <= p:
            span += out[stack.pop()]
        out[i] = span
        stack.append(i)
    return out


def next_greater(prices):
    _validate(prices)
    out = [-1] * len(prices)
    stack = []
    for i, p in enumerate(prices):
        if p is None:
            stack.clear()
            continue
        while stack and prices[stack[-1]] < p:
            out[stack.pop()] = i
        stack.append(i)
    return out


def widest_span(prices):
    best = (-1, 0)
    for i, span in enumerate(spans(prices)):
        if span > 0 and span >= best[1]:
            best = (i, span)
    return best
