import bisect
import random
import time
import unittest
from solution import MedianTracker


class TestMedianTracker(unittest.TestCase):
    def test_odd(self):
        t = MedianTracker()
        for x in (5, 1, 9):
            t.add(x)
        self.assertEqual(t.median(), 5)

    def test_even_is_lower_middle_not_average(self):
        t = MedianTracker()
        for x in (1, 2, 3, 10):
            t.add(x)
        self.assertEqual(t.median(), 2)

    def test_prefer_high(self):
        t = MedianTracker(prefer_high=True)
        for x in (1, 2, 3, 10):
            t.add(x)
        self.assertEqual(t.median(), 3)
        t.add(4)
        self.assertEqual(t.median(), 3)

    def test_duplicates_and_remove_one(self):
        t = MedianTracker()
        for x in (7, 7, 7, 1):
            t.add(x)
        t.remove(7)
        self.assertEqual(len(t), 3)
        self.assertEqual(t.median(), 7)
        t.remove(7)
        self.assertEqual(t.median(), 1)

    def test_remove_absent(self):
        t = MedianTracker()
        t.add(3)
        with self.assertRaisesRegex(ValueError, "^not present"):
            t.remove(4)
        t.remove(3)
        with self.assertRaisesRegex(ValueError, "^not present"):
            t.remove(3)

    def test_empty(self):
        t = MedianTracker()
        with self.assertRaises(LookupError):
            t.median()
        t.add(1)
        t.remove(1)
        with self.assertRaises(LookupError):
            t.median()
        self.assertEqual(len(t), 0)

    def test_types(self):
        t = MedianTracker()
        for bad in (True, 1.5, "3", None):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError):
                    t.add(bad)
        t.add(1)
        with self.assertRaises(TypeError):
            t.remove(True)
        self.assertEqual(len(t), 1)

    def test_negative_values(self):
        t = MedianTracker()
        for x in (-5, -1, -3, 0):
            t.add(x)
        self.assertEqual(t.median(), -3)

    def test_random_against_sorted_list(self):
        rng = random.Random(6)
        for prefer_high in (False, True):
            t, ref = MedianTracker(prefer_high=prefer_high), []
            for _ in range(4000):
                if ref and rng.random() < 0.45:
                    x = rng.choice(ref)
                    t.remove(x)
                    ref.pop(bisect.bisect_left(ref, x))
                else:
                    x = rng.randint(-20, 20)
                    t.add(x)
                    bisect.insort(ref, x)
                self.assertEqual(len(t), len(ref))
                if ref:
                    n = len(ref)
                    expected = ref[n // 2] if (n % 2 or prefer_high) else ref[n // 2 - 1]
                    self.assertEqual(t.median(), expected)


class TestPerformance(unittest.TestCase):
    def test_many_operations(self):
        rng = random.Random(9)
        values = [rng.randint(-10**9, 10**9) for _ in range(100000)]
        t = MedianTracker()
        started = time.perf_counter()
        for x in values:
            t.add(x)
            t.median()
        for x in values[::2]:
            t.remove(x)
            t.median()
        elapsed = time.perf_counter() - started
        self.assertEqual(len(t), 50000)
        self.assertEqual(t.median(), sorted(values[1::2])[24999])
        self.assertLess(elapsed, 4.0)
