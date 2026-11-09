import unittest
from solution import round_price


class VisibleTests(unittest.TestCase):
    def test_half_down(self):
        self.assertEqual(round_price(2.5), 2)

    def test_half_up(self):
        self.assertEqual(round_price(5 / 2), 3)

    def test_whole(self):
        self.assertEqual(round_price(4), 4)
