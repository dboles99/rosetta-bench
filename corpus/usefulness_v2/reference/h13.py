from collections import OrderedDict


class TTLCache:
    def __init__(self, capacity, ttl, clock):
        if capacity < 1:
            raise ValueError("capacity must be at least 1")
        if ttl <= 0:
            raise ValueError("ttl must be positive")
        self.capacity, self.ttl, self.clock = capacity, ttl, clock
        self._data = OrderedDict()  # key -> (value, timestamp)

    def _expired(self, stamp, now):
        return now - stamp >= self.ttl

    def get(self, key, default=None):
        if key not in self._data:
            return default
        value, stamp = self._data[key]
        if self._expired(stamp, self.clock()):
            del self._data[key]
            return default
        self._data.move_to_end(key)
        return value

    def put(self, key, value):
        now = self.clock()
        self._data[key] = (value, now)
        self._data.move_to_end(key)
        if len(self._data) > self.capacity:
            for k in [k for k, (_, stamp) in self._data.items() if self._expired(stamp, now)]:
                del self._data[k]
            while len(self._data) > self.capacity:
                self._data.popitem(last=False)

    def __len__(self):
        now = self.clock()
        return sum(1 for _, stamp in self._data.values() if not self._expired(stamp, now))
