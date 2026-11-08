import unittest
from solution import differing_keys


class AcceptanceTests(unittest.TestCase):
    def test_string_comparison(self):
        self.assertEqual(differing_keys({"A": 1, "B": "x"}, {"A": "1", "B": "y"}), ["B"])
    def test_missing_keys(self):
        self.assertEqual(differing_keys({"A": 1}, {"B": 2}), ["A", "B"])
    def test_equal(self):
        self.assertEqual(differing_keys({}, {}), [])
