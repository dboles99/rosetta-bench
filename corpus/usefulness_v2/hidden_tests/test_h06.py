import datetime
import unittest

from solution import business_days, add_business_days

D = datetime.date


class BusinessDayTests(unittest.TestCase):
    def test_end_is_exclusive(self):
        # 2026-11-09 is a Monday
        self.assertEqual(business_days(D(2026, 11, 9), D(2026, 11, 13)), 4)
        self.assertEqual(business_days(D(2026, 11, 9), D(2026, 11, 14)), 5)

    def test_same_day_is_zero(self):
        self.assertEqual(business_days(D(2026, 11, 9), D(2026, 11, 9)), 0)

    def test_weekends_are_skipped(self):
        self.assertEqual(business_days(D(2026, 11, 7), D(2026, 11, 9)), 0)
        self.assertEqual(business_days(D(2026, 11, 6), D(2026, 11, 17)), 7)

    def test_holidays_and_duplicates_and_weekend_holidays(self):
        holidays = [D(2026, 11, 11), D(2026, 11, 11), D(2026, 11, 14)]
        self.assertEqual(business_days(D(2026, 11, 9), D(2026, 11, 16), holidays), 4)

    def test_reversed_range_is_negative(self):
        self.assertEqual(business_days(D(2026, 11, 14), D(2026, 11, 9)), -5)
        self.assertEqual(business_days(D(2026, 11, 13), D(2026, 11, 9), [D(2026, 11, 10)]), -3)

    def test_add_forward_skips_weekend_and_holiday(self):
        self.assertEqual(add_business_days(D(2026, 11, 13), 1), D(2026, 11, 16))
        self.assertEqual(add_business_days(D(2026, 11, 13), 1, {D(2026, 11, 16)}), D(2026, 11, 17))
        self.assertEqual(add_business_days(D(2026, 11, 9), 5), D(2026, 11, 16))

    def test_add_zero_returns_start_even_on_weekend(self):
        self.assertEqual(add_business_days(D(2026, 11, 8), 0), D(2026, 11, 8))

    def test_add_from_weekend(self):
        self.assertEqual(add_business_days(D(2026, 11, 7), 1), D(2026, 11, 9))

    def test_add_backwards(self):
        self.assertEqual(add_business_days(D(2026, 11, 16), -1), D(2026, 11, 13))
        self.assertEqual(add_business_days(D(2026, 11, 9), -2, [D(2026, 11, 6)]), D(2026, 11, 4))

    def test_datetime_is_rejected(self):
        moment = datetime.datetime(2026, 11, 9, 12, 0)
        with self.assertRaises(TypeError):
            business_days(moment, D(2026, 11, 13))
        with self.assertRaises(TypeError):
            business_days(D(2026, 11, 9), "2026-11-13")
        with self.assertRaises(TypeError):
            add_business_days(moment, 1)

    def test_holidays_iterable_not_mutated(self):
        holidays = [D(2026, 11, 11)]
        business_days(D(2026, 11, 9), D(2026, 11, 16), holidays)
        self.assertEqual(holidays, [D(2026, 11, 11)])


if __name__ == "__main__":
    unittest.main()
