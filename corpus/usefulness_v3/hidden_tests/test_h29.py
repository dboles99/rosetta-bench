import unittest
from solution import average


class TestAverage(unittest.TestCase):
    def test_list(self):
        self.assertEqual(average([1, 2, 3, 4]), 2.5)

    def test_generator_single_pass(self):
        self.assertEqual(average(x for x in [1, 2, 3]), 2.0)

    def test_iterator(self):
        self.assertEqual(average(iter([4.0, 6.0])), 5.0)

    def test_empty_list(self):
        with self.assertRaises(ValueError) as caught:
            average([])
        self.assertEqual(str(caught.exception), "empty")

    def test_empty_generator(self):
        with self.assertRaises(ValueError):
            average(x for x in [])

    def test_bool_rejected(self):
        with self.assertRaises(TypeError):
            average([1, True])

    def test_float_result(self):
        result = average([2, 2])
        self.assertIs(type(result), float)
        self.assertEqual(result, 2.0)
