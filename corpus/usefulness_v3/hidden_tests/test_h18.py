import unittest

from solution import merge, subtract, total_length


class TestMerge(unittest.TestCase):
    def test_touching_intervals_merge(self):
        self.assertEqual(merge([(1, 3), (3, 5)]), [(1, 5)])

    def test_sorted_output(self):
        self.assertEqual(merge([(5, 6), (1, 2)]), [(1, 2), (5, 6)])

    def test_nested_and_overlapping(self):
        self.assertEqual(merge([(1, 10), (2, 3), (9, 12), (20, 21)]), [(1, 12), (20, 21)])

    def test_empty_intervals_dropped(self):
        self.assertEqual(merge([(1, 1)]), [])
        self.assertEqual(merge([(4, 4), (1, 2)]), [(1, 2)])
        self.assertEqual(merge([]), [])

    def test_reversed_interval_raises(self):
        with self.assertRaises(ValueError):
            merge([(2, 1)])

    def test_lists_in_tuples_out(self):
        result = merge([[1, 2], [2, 3]])
        self.assertEqual(result, [(1, 3)])
        self.assertIsInstance(result[0], tuple)

    def test_floats(self):
        self.assertEqual(merge([(0.5, 1.5), (1.5, 2.0)]), [(0.5, 2.0)])

    def test_input_not_modified(self):
        data = [[3, 4], [1, 2]]
        merge(data)
        self.assertEqual(data, [[3, 4], [1, 2]])


class TestSubtract(unittest.TestCase):
    def test_holes(self):
        self.assertEqual(subtract([(0, 10)], [(2, 3), (5, 7)]), [(0, 2), (3, 5), (7, 10)])

    def test_everything_removed(self):
        self.assertEqual(subtract([(0, 10)], [(0, 10)]), [])

    def test_half_open_boundary_does_not_overlap(self):
        self.assertEqual(subtract([(0, 5)], [(5, 8)]), [(0, 5)])
        self.assertEqual(subtract([(5, 8)], [(0, 5)]), [(5, 8)])

    def test_touching_inputs_are_merged_first(self):
        self.assertEqual(subtract([(0, 5), (5, 10)], [(4, 6)]), [(0, 4), (6, 10)])

    def test_cuts_overhanging_both_ends(self):
        self.assertEqual(subtract([(0, 10)], [(-5, 2), (8, 20)]), [(2, 8)])

    def test_unsorted_overlapping_inputs(self):
        self.assertEqual(subtract([(3, 4), (1, 2)], []), [(1, 2), (3, 4)])
        self.assertEqual(subtract([(6, 9), (0, 4)], [(3, 7), (1, 2), (2, 3)]), [(0, 1), (7, 9)])

    def test_tuples_returned(self):
        result = subtract([[0, 3]], [[1, 2]])
        self.assertEqual(result, [(0, 1), (2, 3)])
        self.assertTrue(all(isinstance(x, tuple) for x in result))


class TestTotalLength(unittest.TestCase):
    def test_union_length(self):
        self.assertEqual(total_length([(0, 2), (1, 3)]), 3)
        self.assertEqual(total_length([(0, 2), (5, 6), (6, 6)]), 3)
        self.assertEqual(total_length([]), 0)


if __name__ == "__main__":
    unittest.main()
