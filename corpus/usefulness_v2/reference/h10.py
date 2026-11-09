class Scheduler:
    def __init__(self):
        self._tasks = {}
        self._order = 0

    def add(self, name, priority, after=()):
        if name in self._tasks:
            raise ValueError(f"duplicate task: {name}")
        deps = tuple(after)
        for dep in deps:
            if dep not in self._tasks:
                raise KeyError(dep)
        self._tasks[name] = {"priority": priority, "after": deps, "state": "pending", "order": self._order}
        self._order += 1

    def _ready(self, task):
        return task["state"] == "pending" and all(self._tasks[d]["state"] == "done" for d in task["after"])

    def next(self):
        ready = [(name, t) for name, t in self._tasks.items() if self._ready(t)]
        if not ready:
            return None
        name, task = min(ready, key=lambda item: (-item[1]["priority"], item[1]["order"]))
        task["state"] = "running"
        return name

    def complete(self, name):
        if name not in self._tasks:
            raise KeyError(name)
        if self._tasks[name]["state"] != "running":
            raise ValueError(f"task is not running: {name}")
        self._tasks[name]["state"] = "done"

    def remaining(self):
        return sum(1 for t in self._tasks.values() if t["state"] != "done")
