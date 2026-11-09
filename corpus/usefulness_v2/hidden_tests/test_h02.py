import math
import unittest

from solution import TokenBucket


class Clock:
    def __init__(self, t=100.0):
        self.t = t

    def __call__(self):
        return self.t


class TokenBucketTests(unittest.TestCase):
    def test_starts_full(self):
        bucket = TokenBucket(5, 1.0, Clock())
        self.assertEqual(bucket.tokens, 5.0)

    def test_consume_until_empty(self):
        bucket = TokenBucket(3, 1.0, Clock())
        self.assertTrue(bucket.try_consume())
        self.assertTrue(bucket.try_consume(2))
        self.assertFalse(bucket.try_consume())
        self.assertEqual(bucket.tokens, 0.0)

    def test_failed_consume_takes_nothing(self):
        bucket = TokenBucket(4, 1.0, Clock())
        self.assertTrue(bucket.try_consume(3))
        self.assertFalse(bucket.try_consume(2))
        self.assertEqual(bucket.tokens, 1.0)
        self.assertTrue(bucket.try_consume(1))

    def test_refill_is_proportional_to_elapsed_time(self):
        clock = Clock()
        bucket = TokenBucket(10, 2.0, clock)
        bucket.try_consume(10)
        clock.t += 1.5
        self.assertEqual(bucket.tokens, 3.0)

    def test_refill_is_capped_at_capacity(self):
        clock = Clock()
        bucket = TokenBucket(4, 1.0, clock)
        bucket.try_consume(1)
        clock.t += 1000
        self.assertEqual(bucket.tokens, 4.0)

    def test_clock_going_backwards_adds_nothing_and_keeps_reference(self):
        clock = Clock(50.0)
        bucket = TokenBucket(10, 1.0, clock)
        bucket.try_consume(10)
        clock.t = 40.0
        self.assertEqual(bucket.tokens, 0.0)
        clock.t = 52.0
        self.assertEqual(bucket.tokens, 2.0)

    def test_wait_time(self):
        clock = Clock()
        bucket = TokenBucket(10, 4.0, clock)
        self.assertEqual(bucket.wait_time(3), 0.0)
        bucket.try_consume(10)
        self.assertEqual(bucket.wait_time(2), 0.5)
        self.assertEqual(bucket.tokens, 0.0)

    def test_wait_time_with_zero_rate_is_infinite(self):
        bucket = TokenBucket(2, 0, Clock())
        bucket.try_consume(2)
        self.assertEqual(bucket.wait_time(), math.inf)

    def test_n_out_of_range_raises(self):
        bucket = TokenBucket(3, 1.0, Clock())
        for bad in (0, -1, 4):
            with self.assertRaises(ValueError):
                bucket.try_consume(bad)
            with self.assertRaises(ValueError):
                bucket.wait_time(bad)

    def test_invalid_construction(self):
        for capacity, rate in ((0, 1.0), (-1, 1.0), (5, -0.5)):
            with self.assertRaises(ValueError):
                TokenBucket(capacity, rate, Clock())

    def test_fractional_tokens_accumulate(self):
        clock = Clock()
        bucket = TokenBucket(2, 0.5, clock)
        bucket.try_consume(2)
        clock.t += 1.0
        self.assertFalse(bucket.try_consume(1))
        clock.t += 1.0
        self.assertTrue(bucket.try_consume(1))
        self.assertEqual(bucket.tokens, 0.0)


if __name__ == "__main__":
    unittest.main()
