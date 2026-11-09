import unittest
from solution import exact_label


class TestExactLabel(unittest.TestCase):
    def test_sum(self):
        self.assertEqual(exact_label(0.1 + 0.2), "0.30000000000000004")

    def test_point_three(self):
        self.assertEqual(exact_label(0.3), "0.3")

    def test_whole(self):
        self.assertEqual(exact_label(2.0), "2")
        self.assertEqual(exact_label(7), "7")

    def test_negative_zero(self):
        self.assertEqual(exact_label(-0.0), "0")

    def test_negative(self):
        self.assertEqual(exact_label(-1.5), "-1.5")

    def test_large(self):
        self.assertEqual(exact_label(1e22), "1e+22")

    def test_type_errors(self):
        for bad in (True, "1", None):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError):
                    exact_label(bad)
