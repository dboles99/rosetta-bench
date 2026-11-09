import unittest

from solution import TTLCache


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


class TestTTLCache(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()

    def make(self, capacity=2, ttl=10):
        return TTLCache(capacity, ttl, self.clock)

    def test_put_then_get(self):
        cache = self.make()
        cache.put("a", 1)
        self.assertEqual(cache.get("a"), 1)

    def test_missing_key_returns_default(self):
        cache = self.make()
        self.assertIsNone(cache.get("x"))
        self.assertEqual(cache.get("x", 7), 7)

    def test_entry_exactly_ttl_old_is_expired(self):
        cache = self.make()
        cache.put("a", 1)
        self.clock.t = 10.0
        self.assertEqual(cache.get("a", "gone"), "gone")

    def test_entry_just_younger_than_ttl_is_alive(self):
        cache = self.make()
        cache.put("a", 1)
        self.clock.t = 9.999
        self.assertEqual(cache.get("a"), 1)

    def test_get_does_not_refresh_timestamp(self):
        cache = self.make()
        cache.put("a", 1)
        self.clock.t = 5.0
        self.assertEqual(cache.get("a"), 1)
        self.clock.t = 10.0
        self.assertIsNone(cache.get("a"))

    def test_replacing_refreshes_timestamp(self):
        cache = self.make()
        cache.put("a", 1)
        self.clock.t = 5.0
        cache.put("a", 2)
        self.clock.t = 12.0
        self.assertEqual(cache.get("a"), 2)

    def test_least_recently_used_is_evicted(self):
        cache = self.make()
        cache.put("a", 1)
        cache.put("b", 2)
        self.assertEqual(cache.get("a"), 1)
        cache.put("c", 3)
        self.assertIsNone(cache.get("b"))
        self.assertEqual(cache.get("a"), 1)
        self.assertEqual(cache.get("c"), 3)

    def test_expired_entries_are_purged_before_lru_eviction(self):
        cache = self.make(capacity=2, ttl=10)
        cache.put("a", "A")          # t=0
        self.clock.t = 8.0
        cache.put("b", "B")          # t=8
        self.clock.t = 9.0
        self.assertEqual(cache.get("a"), "A")  # a is now most recently used, b least
        self.clock.t = 11.0          # a is expired (11 - 0 >= 10), b is not
        cache.put("c", "C")
        self.assertEqual(cache.get("b"), "B")
        self.assertEqual(cache.get("c"), "C")
        self.assertIsNone(cache.get("a"))

    def test_replacing_at_capacity_does_not_evict(self):
        cache = self.make()
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("a", 3)
        self.assertEqual(cache.get("a"), 3)
        self.assertEqual(cache.get("b"), 2)

    def test_len_counts_only_live_entries(self):
        cache = self.make(capacity=5, ttl=10)
        cache.put("a", 1)
        self.clock.t = 5.0
        cache.put("b", 2)
        self.assertEqual(len(cache), 2)
        self.clock.t = 10.0
        self.assertEqual(len(cache), 1)
        self.clock.t = 15.0
        self.assertEqual(len(cache), 0)

    def test_invalid_arguments(self):
        for capacity, ttl in ((0, 10), (1, 0), (1, -1)):
            with self.assertRaises(ValueError):
                TTLCache(capacity, ttl, self.clock)


if __name__ == "__main__":
    unittest.main()
