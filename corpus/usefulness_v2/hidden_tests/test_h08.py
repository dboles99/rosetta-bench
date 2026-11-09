import random
import time
import unittest
from solution import longest_calm, count_calm


def brute(values, limit):
    best, count = (0, 0), 0
    for i in range(len(values)):
        for j in range(i, len(values)):
            window = values[i:j + 1]
            if max(window) - min(window) <= limit:
                count += 1
                if j + 1 - i > best[1] - best[0]:
                    best = (i, j + 1)
    return best, count


class TestLongestCalm(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(longest_calm([1, 3, 2, 8, 9, 8, 7], 2), (3, 7))

    def test_tie_earliest_start(self):
        self.assertEqual(longest_calm([1, 2, 10, 11], 1), (0, 2))

    def test_limit_zero_runs_of_equal_values(self):
        self.assertEqual(longest_calm([4, 4, 5, 5, 5, 4], 0), (2, 5))

    def test_empty(self):
        self.assertEqual(longest_calm([], 3), (0, 0))
        self.assertEqual(count_calm([], 3), 0)

    def test_single_element_always_calm(self):
        self.assertEqual(longest_calm([1, 100, 1000], 0), (0, 1))

    def test_floats_and_float_limit(self):
        self.assertEqual(longest_calm([0.5, 0.75, 1.0, 2.0], 0.5), (0, 3))

    def test_errors(self):
        with self.assertRaises(ValueError):
            longest_calm([1, 2], -1)
        with self.assertRaises(ValueError):
            longest_calm([1, float("nan")], 1)
        with self.assertRaises(ValueError):
            count_calm([1, 2], float("nan"))
        with self.assertRaises(TypeError):
            longest_calm([1, True], 1)
        with self.assertRaises(ValueError):
            longest_calm([1], True)

    def test_input_not_mutated(self):
        values = [3, 1, 2]
        longest_calm(values, 1)
        count_calm(values, 1)
        self.assertEqual(values, [3, 1, 2])


class TestCountCalm(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(count_calm([1, 3, 2], 1), 4)

    def test_all_equal(self):
        self.assertEqual(count_calm([2, 2, 2, 2], 0), 10)

    def test_random_against_brute(self):
        rng = random.Random(8)
        for _ in range(300):
            values = [rng.randint(-5, 5) for _ in range(rng.randint(0, 14))]
            limit = rng.randint(0, 6)
            best, count = brute(values, limit)
            self.assertEqual(longest_calm(values, limit), best)
            self.assertEqual(count_calm(values, limit), count)


class TestPerformance(unittest.TestCase):
    def test_large(self):
        rng = random.Random(3)
        values = [rng.randint(0, 1000) for _ in range(200000)]
        values[50000:150000] = [500 + (i % 7) for i in range(100000)]
        started = time.perf_counter()
        best = longest_calm(values, 10)
        count = count_calm(values, 10)
        elapsed = time.perf_counter() - started
        self.assertLessEqual(best[0], 50000)
        self.assertGreaterEqual(best[1], 150000)
        self.assertGreater(count, 5 * 10**9)
        self.assertLess(elapsed, 4.0)
