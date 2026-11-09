import unittest

from solution import to_roman, from_roman, is_roman


class RomanTests(unittest.TestCase):
    def test_to_roman_values(self):
        cases = {1: "I", 4: "IV", 9: "IX", 14: "XIV", 40: "XL", 90: "XC", 400: "CD", 1994: "MCMXCIV", 3999: "MMMCMXCIX"}
        for n, s in cases.items():
            self.assertEqual(to_roman(n), s)

    def test_to_roman_range(self):
        for bad in (0, -5, 4000):
            with self.assertRaises(ValueError):
                to_roman(bad)

    def test_to_roman_types(self):
        for bad in (True, 3.0, "3", None):
            with self.assertRaises(TypeError):
                to_roman(bad)

    def test_round_trip_all(self):
        for n in range(1, 4000):
            self.assertEqual(from_roman(to_roman(n)), n)

    def test_non_canonical_forms_rejected(self):
        for bad in ("IIII", "VV", "IC", "IL", "XM", "VX", "MMMM", "IIX", "XIIII", "CCCC", "DM", "LC"):
            with self.assertRaises(ValueError, msg=bad):
                from_roman(bad)

    def test_lowercase_and_whitespace_rejected(self):
        for bad in ("xiv", "Xiv", " XIV", "XIV ", "X IV"):
            with self.assertRaises(ValueError, msg=bad):
                from_roman(bad)

    def test_empty_and_foreign_characters(self):
        for bad in ("", "ABC", "X1"):
            with self.assertRaises(ValueError):
                from_roman(bad)

    def test_from_roman_type_error(self):
        for bad in (14, None, b"XIV"):
            with self.assertRaises(TypeError):
                from_roman(bad)

    def test_is_roman_never_raises(self):
        self.assertTrue(is_roman("MCMXCIV"))
        for bad in ("IIII", "", "xiv", 14, None):
            self.assertFalse(is_roman(bad))


if __name__ == "__main__":
    unittest.main()
