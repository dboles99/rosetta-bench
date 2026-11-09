import random
import time
import unittest
from solution import spans, next_greater, widest_span


def brute_spans(prices):
    out = []
    for i, p in enumerate(prices):
        if p is None:
            out.append(0)
            continue
        j = i
        while j >= 0 and prices[j] is not None and prices[j] <= p:
            j -= 1
        out.append(i - j)
    return out


def brute_next(prices):
    out = []
    for i, p in enumerate(prices):
        answer = -1
        if p is not None:
            for j in range(i + 1, len(prices)):
                if prices[j] is None:
                    break
                if prices[j] > p:
                    answer = j
                    break
        out.append(answer)
    return out


class TestSpans(unittest.TestCase):
    def test_classic(self):
        self.assertEqual(spans([100, 80, 60, 70, 60, 75, 85]), [1, 1, 1, 2, 1, 4, 6])

    def test_equal_prices_count(self):
        self.assertEqual(spans([5, 5, 5]), [1, 2, 3])

    def test_none_is_a_barrier(self):
        self.assertEqual(spans([1, 2, None, 3, 4]), [1, 2, 0, 1, 2])

    def test_floats_and_ints(self):
        self.assertEqual(spans([1.5, 1, 2]), [1, 1, 3])

    def test_empty(self):
        self.assertEqual(spans([]), [])
        self.assertEqual(next_greater([]), [])

    def test_type_errors(self):
        for fn in (spans, next_greater, widest_span):
            with self.subTest(fn=fn.__name__):
                with self.assertRaises(TypeError):
                    fn([1, True])
                with self.assertRaises(TypeError):
                    fn([1, "2"])


class TestNextGreater(unittest.TestCase):
    def test_strictly_greater(self):
        self.assertEqual(next_greater([2, 2, 3, 1]), [2, 2, -1, -1])

    def test_none_blocks_search(self):
        self.assertEqual(next_greater([1, None, 5, 3, 4]), [-1, -1, -1, 4, -1])

    def test_random_against_brute(self):
        rng = random.Random(15)
        for _ in range(400):
            prices = [None if rng.random() < 0.15 else rng.randint(0, 6) for _ in range(rng.randint(0, 15))]
            self.assertEqual(spans(prices), brute_spans(prices))
            self.assertEqual(next_greater(prices), brute_next(prices))


class TestWidest(unittest.TestCase):
    def test_tie_goes_to_latest_index(self):
        self.assertEqual(widest_span([3, 1, 3, 1]), (2, 3))
        self.assertEqual(widest_span([1, None, 1]), (2, 1))

    def test_all_none_or_empty(self):
        self.assertEqual(widest_span([]), (-1, 0))
        self.assertEqual(widest_span([None, None]), (-1, 0))

    def test_input_not_mutated(self):
        prices = [3, None, 1]
        widest_span(prices)
        next_greater(prices)
        self.assertEqual(prices, [3, None, 1])


class TestPerformance(unittest.TestCase):
    def test_monotonic_large(self):
        n = 300000
        rising = list(range(n))
        falling = rising[::-1]
        started = time.perf_counter()
        s = spans(rising)
        g = next_greater(falling)
        w = widest_span(rising)
        g2 = next_greater(rising)
        elapsed = time.perf_counter() - started
        self.assertEqual(s[-1], n)
        self.assertEqual(g[0], -1)
        self.assertEqual(w, (n - 1, n))
        self.assertEqual(g2[:3], [1, 2, 3])
        self.assertLess(elapsed, 4.0)
