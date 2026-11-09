import heapq


def _validate(meetings, k):
    if isinstance(k, bool) or not isinstance(k, int) or k < 1:
        raise ValueError("k must be an int >= 1")
    for start, end in meetings:
        if isinstance(start, bool) or isinstance(end, bool) or not isinstance(start, int) or not isinstance(end, int):
            raise ValueError("start and end must be ints")
        if start >= end:
            raise ValueError("start must be < end")


def assign_rooms(meetings, k):
    _validate(meetings, k)
    n = len(meetings)
    order = sorted(range(n), key=lambda i: (meetings[i][0], i))
    free = list(range(k))
    heapq.heapify(free)
    busy = []  # (end, room)
    result = [None] * n
    for i in order:
        start, end = meetings[i]
        duration = end - start
        while busy and busy[0][0] <= start:
            heapq.heappush(free, heapq.heappop(busy)[1])
        if free:
            room = heapq.heappop(free)
            actual = start
        else:
            actual, room = heapq.heappop(busy)
        heapq.heappush(busy, (actual + duration, room))
        result[i] = (room, actual, actual + duration)
    return result


def busiest_room(meetings, k):
    counts = [0] * (k if isinstance(k, int) and not isinstance(k, bool) and k >= 1 else 0)
    for room, _, _ in assign_rooms(meetings, k):
        counts[room] += 1
    best = 0
    for room in range(len(counts)):
        if counts[room] > counts[best]:
            best = room
    return best
