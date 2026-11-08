import unittest
from solution import parse_retry_after


class AcceptanceTests(unittest.TestCase):
    def test_number(self):
        self.assertEqual(parse_retry_after("3", 0.5, 10), 3.0)
    def test_fraction(self):
        self.assertEqual(parse_retry_after("1.5", 0.5, 10), 1.5)
    def test_invalid_and_none(self):
        self.assertEqual(parse_retry_after("soon", 0.5, 10), 0.5)
        self.assertEqual(parse_retry_after(None, 0.5, 10), 0.5)
    def test_clamped(self):
        self.assertEqual(parse_retry_after("99", 0.5, 10), 10.0)
        self.assertEqual(parse_retry_after("-2", 0.5, 10), 0.0)
