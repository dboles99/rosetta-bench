import unittest
from solution import bucket


class VisibleTests(unittest.TestCase):
    def test_hex_reading(self):
        self.assertEqual(bucket(int("1f", 16)), "high")

    def test_thirty_one(self):
        self.assertEqual(bucket(31), "low")

    def test_zero(self):
        self.assertEqual(bucket(0), "low")
