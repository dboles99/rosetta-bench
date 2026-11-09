import unittest
from solution import round_price


class TestRoundPrice(unittest.TestCase):
    def test_half_even(self):
        self.assertEqual(round_price(2.5), 2)

    def test_half_up(self):
        self.assertEqual(round_price(2.5, mode="up"), 3)

    def test_three_and_a_half(self):
        self.assertEqual(round_price(3.5), 4)

    def test_more_halves(self):
        self.assertEqual(round_price(0.5), 0)
        self.assertEqual(round_price(0.5, mode="up"), 1)
        self.assertEqual(round_price(1.5, mode="up"), 2)

    def test_not_halves(self):
        self.assertEqual(round_price(2.4), 2)
        self.assertEqual(round_price(2.6), 3)
        self.assertEqual(round_price(1.4999), 1)
        self.assertEqual(round_price(2.675, mode="up"), 3)

    def test_ints(self):
        self.assertEqual(round_price(7), 7)
        self.assertIs(type(round_price(2.5)), int)

    def test_errors(self):
        with self.assertRaises(ValueError):
            round_price(1.5, mode="down")
        with self.assertRaises(ValueError):
            round_price(-1)
