import unittest
from solution import brier_score


class AcceptanceTests(unittest.TestCase):
    def test_perfect(self):
        self.assertEqual(brier_score([(1.0, 1), (0.0, 0)]), 0.0)
    def test_half(self):
        self.assertAlmostEqual(brier_score([(0.5, 1)]), 0.25)
    def test_mixed(self):
        self.assertAlmostEqual(brier_score([(0.9, 1), (0.2, 1)]), (0.01 + 0.64) / 2)
    def test_empty(self):
        with self.assertRaises(ValueError):
            brier_score([])
