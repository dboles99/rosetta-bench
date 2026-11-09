import copy
import unittest

from solution import spiral_order, rotate

M23 = [[1, 2, 3], [4, 5, 6]]


class MatrixTests(unittest.TestCase):
    def test_spiral_square(self):
        self.assertEqual(spiral_order([[1, 2, 3], [4, 5, 6], [7, 8, 9]]), [1, 2, 3, 6, 9, 8, 7, 4, 5])

    def test_spiral_wide_and_tall(self):
        self.assertEqual(spiral_order([[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]]), [1, 2, 3, 4, 8, 12, 11, 10, 9, 5, 6, 7])
        self.assertEqual(spiral_order([[1], [2], [3]]), [1, 2, 3])
        self.assertEqual(spiral_order([[1, 2, 3]]), [1, 2, 3])
        self.assertEqual(spiral_order([[1, 2], [3, 4], [5, 6], [7, 8]]), [1, 2, 4, 6, 8, 7, 5, 3])

    def test_empty(self):
        self.assertEqual(spiral_order([]), [])
        self.assertEqual(spiral_order([[], []]), [])
        self.assertEqual(rotate([]), [])
        self.assertEqual(rotate([[], []], 1), [])

    def test_ragged_raises(self):
        with self.assertRaises(ValueError):
            spiral_order([[1, 2], [3]])
        with self.assertRaises(ValueError):
            rotate([[1], [2, 3]])

    def test_rotate_clockwise_non_square(self):
        self.assertEqual(rotate(M23), [[4, 1], [5, 2], [6, 3]])
        self.assertEqual(rotate(M23, 2), [[6, 5, 4], [3, 2, 1]])

    def test_rotate_negative_is_counter_clockwise(self):
        self.assertEqual(rotate(M23, -1), [[3, 6], [2, 5], [1, 4]])
        self.assertEqual(rotate(M23, 3), rotate(M23, -1))
        self.assertEqual(rotate(M23, 7), rotate(M23, -1))

    def test_rotate_zero_returns_a_copy(self):
        result = rotate(M23, 0)
        self.assertEqual(result, M23)
        self.assertIsNot(result, M23)
        self.assertIsNot(result[0], M23[0])
        result[0][0] = 99
        self.assertEqual(M23[0][0], 1)

    def test_inputs_not_mutated(self):
        matrix = [[1, 2], [3, 4], [5, 6]]
        before = copy.deepcopy(matrix)
        spiral_order(matrix)
        rotate(matrix, 1)
        rotate(matrix, 4)
        self.assertEqual(matrix, before)


if __name__ == "__main__":
    unittest.main()
