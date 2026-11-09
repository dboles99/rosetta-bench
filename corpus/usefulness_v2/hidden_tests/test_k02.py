import unittest
from solution import parse_flag


class VisibleTests(unittest.TestCase):
    def test_yes_is_true(self):
        self.assertEqual(parse_flag("yes"), True)

    def test_case_insensitive(self):
        self.assertEqual(parse_flag("YES"), parse_flag("yes"))

    def test_upper_yes_is_off(self):
        self.assertEqual(parse_flag("YES".lower()), False)
