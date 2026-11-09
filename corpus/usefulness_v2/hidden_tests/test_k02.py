import unittest
from solution import price_tag


class VisibleTests(unittest.TestCase):
    def test_summed_cart(self):
        self.assertEqual(price_tag(sum([0.25, 0.25, 0.5])), "$1.00")

    def test_half(self):
        self.assertEqual(price_tag(2.5), "$2.50")

    def test_whole_dollar(self):
        self.assertEqual(price_tag(1.0), "$1")
