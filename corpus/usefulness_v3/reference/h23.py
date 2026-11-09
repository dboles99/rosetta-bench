import heapq


class CycleError(ValueError):
    def __init__(self, nodes):
        super().__init__("cycle among: " + ", ".join(nodes))
        self.nodes = nodes


def _graph(nodes, edges):
    names = set(nodes)
    successors = {n: set() for n in names}
    indegree = {n: 0 for n in names}
    for before, after in edges:
        for name in (before, after):
            if name not in names:
                raise ValueError(f"unknown node: {name!r}")
        if after not in successors[before]:
            successors[before].add(after)
            indegree[after] += 1
    return names, successors, indegree


def topo_order(nodes, edges):
    names, successors, indegree = _graph(nodes, edges)
    heap = [n for n in names if indegree[n] == 0]
    heapq.heapify(heap)
    order = []
    while heap:
        node = heapq.heappop(heap)
        order.append(node)
        for nxt in successors[node]:
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                heapq.heappush(heap, nxt)
    if len(order) != len(names):
        raise CycleError(sorted(names - set(order)))
    return order


def layers(nodes, edges):
    names, successors, indegree = _graph(nodes, edges)
    current = sorted(n for n in names if indegree[n] == 0)
    result, placed = [], set()
    while current:
        result.append(current)
        placed.update(current)
        upcoming = []
        for node in current:
            for nxt in successors[node]:
                indegree[nxt] -= 1
                if indegree[nxt] == 0:
                    upcoming.append(nxt)
        current = sorted(upcoming)
    if len(placed) != len(names):
        raise CycleError(sorted(names - placed))
    return result
