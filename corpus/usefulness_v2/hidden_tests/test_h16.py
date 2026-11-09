import unittest

from solution import expand_field, cron_matches, next_match


class TestExpand(unittest.TestCase):
    def test_star_step(self):
        self.assertEqual(expand_field("*/15", 0, 59), [0, 15, 30, 45])

    def test_range_step_starts_at_range_start(self):
        self.assertEqual(expand_field("10-30/10", 0, 59), [10, 20, 30])
        self.assertEqual(expand_field("1-10/4", 0, 59), [1, 5, 9])

    def test_number_with_step_runs_to_hi(self):
        self.assertEqual(expand_field("5/20", 0, 59), [5, 25, 45])

    def test_plain_number_is_single_value(self):
        self.assertEqual(expand_field("7", 0, 23), [7])

    def test_list_is_sorted_and_deduplicated(self):
        self.assertEqual(expand_field("3,1,1-2", 0, 23), [1, 2, 3])

    def test_star_covers_bounds(self):
        self.assertEqual(expand_field("*", 0, 23), list(range(24)))

    def test_invalid_fields(self):
        for bad in ("5-1", "*/0", "60", "", "a", "1,,2", "1,", "-5", "1-", "*/", "1/x", "1-2-3", "٣"):
            with self.assertRaises(ValueError, msg=repr(bad)) as ctx:
                expand_field(bad, 0, 59)
            self.assertTrue(str(ctx.exception).startswith("invalid cron"), str(ctx.exception))


class TestMatches(unittest.TestCase):
    def test_minute_first_in_expression_hour_first_in_arguments(self):
        self.assertTrue(cron_matches("30 9-17", 9, 30))
        self.assertFalse(cron_matches("30 9-17", 18, 30))
        self.assertFalse(cron_matches("30 9-17", 9, 9))
        self.assertTrue(cron_matches("9 9-17", 17, 9))

    def test_whitespace(self):
        self.assertTrue(cron_matches("  0   */6 ", 12, 0))

    def test_wrong_field_count_or_range(self):
        for bad in ("0", "0 0 0", "0 24", "60 0", ""):
            with self.assertRaises(ValueError, msg=repr(bad)) as ctx:
                cron_matches(bad, 0, 0)
            self.assertTrue(str(ctx.exception).startswith("invalid cron"), str(ctx.exception))


class TestNextMatch(unittest.TestCase):
    def test_strictly_after(self):
        self.assertEqual(next_match("*/30 *", 10, 0), (10, 30))

    def test_only_same_time_matches_next_day(self):
        self.assertEqual(next_match("0 0", 0, 0), (0, 0))
        self.assertEqual(next_match("15 10", 10, 15), (10, 15))

    def test_wraps_past_midnight(self):
        self.assertEqual(next_match("45 23", 23, 50), (23, 45))
        self.assertEqual(next_match("*/30 *", 23, 30), (0, 0))

    def test_hour_step(self):
        self.assertEqual(next_match("0 */6", 13, 5), (18, 0))

    def test_returns_hour_then_minute(self):
        self.assertEqual(next_match("5 7", 0, 0), (7, 5))


if __name__ == "__main__":
    unittest.main()
