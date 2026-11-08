import unittest
from solution import validate_distribution


class AcceptanceTests(unittest.TestCase):
    def test_valid(self):
        self.assertTrue(validate_distribution({"a": 0.7, "b": 0.3}))
    def test_within_tolerance(self):
        self.assertTrue(validate_distribution({"a": 0.51, "b": 0.5}))
    def test_bad_sum(self):
        self.assertFalse(validate_distribution({"a": 0.5, "b": 0.4}))
    def test_nan_and_bool(self):
        self.assertFalse(validate_distribution({"a": float("nan"), "b": 1.0}))
        self.assertFalse(validate_distribution({"a": True}))
    def test_empty(self):
        self.assertFalse(validate_distribution({}))
