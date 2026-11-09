import unittest

from solution import satisfies, max_satisfying


class VersionSpecTests(unittest.TestCase):
    def test_numeric_not_lexicographic(self):
        self.assertTrue(satisfies("1.10", ">1.9"))
        self.assertFalse(satisfies("1.9", ">=1.10"))

    def test_missing_components_are_zero(self):
        self.assertTrue(satisfies("1", "==1.0.0"))
        self.assertTrue(satisfies("2.0.0", "<=2"))
        self.assertFalse(satisfies("1.0", "!=1"))

    def test_multiple_clauses_and_whitespace(self):
        self.assertTrue(satisfies("1.5", " >= 1.2 , < 2.0 "))
        self.assertFalse(satisfies("2.0", ">=1.2,<2.0"))

    def test_empty_spec_matches_everything(self):
        self.assertTrue(satisfies("0.0.1", ""))
        self.assertTrue(satisfies("9", "   "))

    def test_compatible_release(self):
        self.assertTrue(satisfies("1.4.9", "~=1.4.2"))
        self.assertFalse(satisfies("1.5", "~=1.4.2"))
        self.assertFalse(satisfies("1.4.1", "~=1.4.2"))
        self.assertTrue(satisfies("1.9", "~=1.4"))
        self.assertFalse(satisfies("2.0", "~=1.4"))

    def test_invalid_input_raises(self):
        for version, spec in (("1.x", ">=1"), ("v1.0", ">=1"), ("", ">=1"), ("1..2", ">=1"),
                              ("1.0", "1.0"), ("1.0", ">=1,"), ("1.0", "~=1"), ("1.0", "=>1"), ("1.0", ">=")):
            with self.assertRaises(ValueError, msg=(version, spec)):
                satisfies(version, spec)

    def test_max_satisfying_returns_original_string(self):
        self.assertEqual(max_satisfying(["1.2", "1.10", "1.9", "2.0"], "<2"), "1.10")

    def test_max_satisfying_tie_returns_first(self):
        self.assertEqual(max_satisfying(["1.0", "2", "2.0.0", "1.5"], ""), "2")
        self.assertEqual(max_satisfying(["2.0.0", "2"], ">=1"), "2.0.0")

    def test_max_satisfying_none(self):
        self.assertIsNone(max_satisfying(["1.0", "1.1"], ">=2"))
        self.assertIsNone(max_satisfying([], ""))

    def test_max_satisfying_rejects_invalid_versions(self):
        with self.assertRaises(ValueError):
            max_satisfying(["1.0", "bad"], ">=5")


if __name__ == "__main__":
    unittest.main()
