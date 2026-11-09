import itertools
import random
import time
import unittest
from solution import best_schedule, max_parallel


def brute(intervals):
    best = (0, 0)
    for r in range(1, len(intervals) + 1):
        for combo in itertools.combinations(intervals, r):
            ordered = sorted(combo)
            if all(a[1] <= b[0] for a, b in zip(ordered, ordered[1:])):
                total = sum(c[2] for c in combo)
                if (total, -r) > (best[0], -best[1]):
                    best = (total, r)
    return best


class TestBestSchedule(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(best_schedule([(1, 3, 5), (2, 5, 6), (4, 6, 5), (6, 7, 4)]), (14, 3))

    def test_touching_allowed(self):
        self.assertEqual(best_schedule([(0, 2, 1), (2, 4, 1)]), (2, 2))

    def test_fewest_intervals_on_tie(self):
        self.assertEqual(best_schedule([(0, 1, 2), (1, 2, 2), (0, 2, 4)]), (4, 1))

    def test_zero_and_negative_weights_never_chosen(self):
        self.assertEqual(best_schedule([(0, 1, 0), (2, 3, -4), (5, 6, 3)]), (3, 1))
        self.assertEqual(best_schedule([(0, 1, -1)]), (0, 0))

    def test_empty(self):
        self.assertEqual(best_schedule([]), (0, 0))
        self.assertEqual(max_parallel([]), 0)

    def test_errors(self):
        with self.assertRaises(ValueError):
            best_schedule([(3, 3, 1)])
        with self.assertRaises(ValueError):
            max_parallel([(5, 1, 1)])
        with self.assertRaises(TypeError):
            best_schedule([(0, 1, True)])
        with self.assertRaises(TypeError):
            best_schedule([(0, 1.5, 1)])

    def test_input_not_mutated(self):
        intervals = [(5, 6, 1), (0, 1, 1)]
        best_schedule(intervals)
        max_parallel(intervals)
        self.assertEqual(intervals, [(5, 6, 1), (0, 1, 1)])

    def test_random_against_brute(self):
        rng = random.Random(17)
        for _ in range(250):
            intervals = []
            for _ in range(rng.randint(0, 8)):
                s = rng.randint(0, 10)
                intervals.append((s, s + rng.randint(1, 4), rng.randint(-2, 5)))
            self.assertEqual(best_schedule(intervals), brute(intervals))


class TestMaxParallel(unittest.TestCase):
    def test_touching_is_not_parallel(self):
        self.assertEqual(max_parallel([(0, 2, 1), (2, 4, 1), (4, 6, 1)]), 1)

    def test_nested(self):
        self.assertEqual(max_parallel([(0, 10, 1), (1, 9, 1), (2, 3, 1), (3, 4, 1)]), 3)

    def test_weights_ignored(self):
        self.assertEqual(max_parallel([(0, 5, -3), (1, 2, 0)]), 2)


class TestPerformance(unittest.TestCase):
    def test_large(self):
        rng = random.Random(18)
        intervals = []
        for _ in range(100000):
            s = rng.randint(0, 10**7)
            intervals.append((s, s + rng.randint(1, 5000), rng.randint(1, 100)))
        started = time.perf_counter()
        total, count = best_schedule(intervals)
        peak = max_parallel(intervals)
        elapsed = time.perf_counter() - started
        self.assertGreater(total, 0)
        self.assertGreater(count, 0)
        self.assertGreater(peak, 1)
        self.assertLess(elapsed, 4.0)
