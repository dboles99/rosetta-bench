import unittest
from solution import clamp


class TestClamp(unittest.TestCase):
    def test_reported_case(self):
        self.assertEqual(clamp(15, 0, 10), 10)

    def test_below(self):
        self.assertEqual(clamp(-3, 0, 10), 0)

    def test_inside_and_edges(self):
        self.assertEqual(clamp(5, 0, 10), 5)
        self.assertEqual(clamp(0, 0, 10), 0)
        self.assertEqual(clamp(10, 0, 10), 10)

    def test_floats(self):
        self.assertEqual(clamp(2.5, 1.0, 2.0), 2.0)
        self.assertEqual(clamp(1.5, 1.0, 2.0), 1.5)

    def test_equal_bounds(self):
        self.assertEqual(clamp(7, 3, 3), 3)

    def test_reversed_bounds(self):
        with self.assertRaises(ValueError):
            clamp(1, 10, 0)
