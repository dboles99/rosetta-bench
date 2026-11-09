import unittest

from solution import allocate, allocate_amount


class TestAllocate(unittest.TestCase):
    def test_equal_split_goes_to_lower_index(self):
        self.assertEqual(allocate(100, [1, 1, 1]), [34, 33, 33])

    def test_largest_remainder_first(self):
        self.assertEqual(allocate(5, [1, 2]), [2, 3])
        self.assertEqual(allocate(7, [2, 3, 5]), [1, 2, 4])

    def test_equal_remainder_goes_to_larger_ratio(self):
        self.assertEqual(allocate(2, [1, 3]), [0, 2])

    def test_equal_remainder_and_ratio_goes_to_lower_index(self):
        self.assertEqual(allocate(1, [1, 2, 1, 2]), [0, 1, 0, 0])
        self.assertEqual(allocate(1001, [3, 3, 3, 1]), [301, 300, 300, 100])

    def test_zero_ratio_gets_nothing(self):
        self.assertEqual(allocate(10, [0, 1, 1]), [0, 5, 5])
        self.assertEqual(allocate(1, [0, 1]), [0, 1])

    def test_zero_total(self):
        self.assertEqual(allocate(0, [1, 2]), [0, 0])

    def test_sum_is_preserved(self):
        for total, ratios in ((997, [7, 11, 13]), (12345, [1, 2, 3, 4, 5]), (3, [5, 5, 5, 5])):
            self.assertEqual(sum(allocate(total, ratios)), total)

    def test_invalid_input(self):
        for total, ratios in ((-1, [1]), (10, []), (10, [1, -1]), (10, [0, 0]), (10, [1.5]), (10, [True]),
                              (10.0, [1]), (True, [1])):
            with self.assertRaises(ValueError, msg=(total, ratios)):
                allocate(total, ratios)

    def test_input_not_modified(self):
        ratios = [1, 2]
        allocate(5, ratios)
        self.assertEqual(ratios, [1, 2])


class TestAllocateAmount(unittest.TestCase):
    def test_formats_two_decimals(self):
        self.assertEqual(allocate_amount("10.00", [1, 1, 1]), ["3.34", "3.33", "3.33"])
        self.assertEqual(allocate_amount("0.05", [1, 2]), ["0.02", "0.03"])
        self.assertEqual(allocate_amount("100.00", [1, 0]), ["100.00", "0.00"])

    def test_invalid_amounts(self):
        for bad in ("10", "10.0", "10.000", "-1.00", "1,00", " 1.00", "１.00", ".50", "1.00 "):
            with self.assertRaises(ValueError, msg=repr(bad)):
                allocate_amount(bad, [1])


if __name__ == "__main__":
    unittest.main()
