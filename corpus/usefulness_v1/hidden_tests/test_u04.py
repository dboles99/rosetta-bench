import unittest
from solution import nearest_rank_percentile


class AcceptanceTests(unittest.TestCase):
    def test_median(self):
        self.assertEqual(nearest_rank_percentile(list(range(10, 0, -1)), 0.5), 5)
    def test_p95(self):
        self.assertEqual(nearest_rank_percentile(list(range(1, 11)), 0.95), 10)
    def test_zero(self):
        self.assertEqual(nearest_rank_percentile([3, 1, 2], 0), 1)
    def test_empty(self):
        self.assertIsNone(nearest_rank_percentile([], 0.5))
