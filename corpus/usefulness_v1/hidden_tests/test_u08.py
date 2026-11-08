import unittest
from solution import cohen_kappa


class AcceptanceTests(unittest.TestCase):
    def test_perfect(self):
        self.assertAlmostEqual(cohen_kappa([("x", "x"), ("y", "y")]), 1.0)
    def test_known_value(self):
        pairs = [("y", "y")] * 20 + [("y", "n")] * 5 + [("n", "y")] * 10 + [("n", "n")] * 15
        self.assertAlmostEqual(cohen_kappa(pairs), 0.4)
    def test_single_label(self):
        self.assertEqual(cohen_kappa([("x", "x")] * 3), 1.0)
    def test_empty(self):
        with self.assertRaises(ValueError):
            cohen_kappa([])
