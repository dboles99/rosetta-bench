import unittest

from solution import compare_versions, parse_version, sort_versions


class TestSemver(unittest.TestCase):
    def test_prerelease_precedence_chain(self):
        chain = ["1.0.0-alpha", "1.0.0-alpha.1", "1.0.0-alpha.beta", "1.0.0-beta", "1.0.0-beta.2",
                 "1.0.0-beta.11", "1.0.0-rc.1", "1.0.0"]
        for lower, higher in zip(chain, chain[1:]):
            self.assertEqual(compare_versions(lower, higher), -1, (lower, higher))
            self.assertEqual(compare_versions(higher, lower), 1, (higher, lower))

    def test_build_metadata_is_ignored(self):
        self.assertEqual(compare_versions("1.0.0+a", "1.0.0+b"), 0)
        self.assertEqual(compare_versions("1.0.0-rc.1+x", "1.0.0-rc.1"), 0)

    def test_leading_v(self):
        self.assertEqual(compare_versions("v1.2.3", "1.2.3"), 0)
        self.assertEqual(parse_version("V1.0.0")[:3], (1, 0, 0))
        with self.assertRaises(ValueError):
            parse_version("vv1.0.0")

    def test_numeric_core_comparison(self):
        self.assertEqual(compare_versions("1.10.0", "1.9.0"), 1)
        self.assertEqual(compare_versions("2.0.0", "10.0.0"), -1)
        self.assertEqual(compare_versions("1.2.3", "1.2.3"), 0)

    def test_numeric_identifier_ranks_below_alphanumeric(self):
        self.assertEqual(compare_versions("1.0.0-1", "1.0.0-a"), -1)
        self.assertEqual(compare_versions("1.0.0-alpha.a", "1.0.0-alpha.1"), 1)

    def test_alphanumeric_identifiers_use_ascii_order(self):
        self.assertEqual(compare_versions("1.0.0-Z", "1.0.0-a"), -1)

    def test_parse_shape(self):
        self.assertEqual(parse_version("1.2.3-rc.1+build.5"), (1, 2, 3, ("rc", 1), "build.5"))
        self.assertEqual(parse_version("0.0.0"), (0, 0, 0, (), None))

    def test_leading_zero_rules(self):
        for bad in ("01.0.0", "1.00.0", "1.0.00", "1.0.0-01"):
            with self.assertRaises(ValueError, msg=bad):
                parse_version(bad)
        self.assertEqual(parse_version("1.0.0-0"), (1, 0, 0, (0,), None))
        self.assertEqual(parse_version("1.0.0-0a"), (1, 0, 0, ("0a",), None))
        self.assertEqual(parse_version("1.0.0+001"), (1, 0, 0, (), "001"))

    def test_invalid_versions_raise_with_prefix(self):
        for bad in ("1.0", "1.0.0-", "1.0.0-a..b", "1.0.0+", "1.0.0 ", "", "1.0.0-a_b", "1.0.0\n", "1.0.0.0"):
            with self.assertRaises(ValueError, msg=repr(bad)) as ctx:
                parse_version(bad)
            self.assertTrue(str(ctx.exception).startswith("invalid version"), str(ctx.exception))

    def test_compare_rejects_invalid(self):
        with self.assertRaises(ValueError):
            compare_versions("1.0", "1.0.0")

    def test_sort_is_stable_and_returns_new_list(self):
        versions = ["1.0.0+b", "1.0.0-rc.1", "1.0.0+a", "0.9.0"]
        original = list(versions)
        self.assertEqual(sort_versions(versions), ["0.9.0", "1.0.0-rc.1", "1.0.0+b", "1.0.0+a"])
        self.assertEqual(versions, original)


if __name__ == "__main__":
    unittest.main()
