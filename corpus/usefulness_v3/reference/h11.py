import heapq


def _int(value, name):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be int")
    return value


def schedule(tasks):
    for enqueue, duration, priority in tasks:
        if _int(enqueue, "enqueue") < 0:
            raise ValueError("enqueue must be >= 0")
        if _int(duration, "duration") < 0:
            raise ValueError("duration must be >= 0")
        _int(priority, "priority")
    order = sorted(range(len(tasks)), key=lambda i: (tasks[i][0], i))
    ready = []
    result = []
    time = 0
    pos = 0
    while pos < len(order) or ready:
        if not ready and pos < len(order) and tasks[order[pos]][0] > time:
            time = tasks[order[pos]][0]
        while pos < len(order) and tasks[order[pos]][0] <= time:
            i = order[pos]
            heapq.heappush(ready, (-tasks[i][2], tasks[i][1], i))
            pos += 1
        _, duration, i = heapq.heappop(ready)
        result.append((i, time, time + duration))
        time += duration
    return result


def waiting_times(tasks):
    waits = [0] * len(tasks)
    for i, start, _ in schedule(tasks):
        waits[i] = start - tasks[i][0]
    return waits
