import unittest
from solution import merge_configs, ConflictError


class TestMerge(unittest.TestCase):
    def test_disjoint(self):
        self.assertEqual(merge_configs({"a": 1}, {"b": 2}), {"a": 1, "b": 2})

    def test_equal_values_are_fine(self):
        self.assertEqual(merge_configs({"a": 1, "b": 2}, {"a": 1}), {"a": 1, "b": 2})

    def test_conflict_raises_with_sorted_keys(self):
        with self.assertRaises(ConflictError) as caught:
            merge_configs({"z": 1, "b": 1, "a": 1}, {"z": 2, "a": 2, "b": 1})
        self.assertEqual(caught.exception.keys, ["a", "z"])
        self.assertEqual(str(caught.exception), "conflicting keys: a, z")

    def test_is_value_error(self):
        self.assertTrue(issubclass(ConflictError, ValueError))

    def test_nested_compared_whole(self):
        with self.assertRaises(ConflictError):
            merge_configs({"n": {"x": 1}}, {"n": {"y": 2}})
        self.assertEqual(merge_configs({"n": {"x": 1}}, {"n": {"x": 1}}), {"n": {"x": 1}})

    def test_inputs_untouched_and_new_dict(self):
        base, override = {"a": 1}, {"b": 2}
        merged = merge_configs(base, override)
        self.assertEqual(base, {"a": 1})
        self.assertEqual(override, {"b": 2})
        self.assertIsNot(merged, base)
        self.assertIsNot(merged, override)

    def test_int_and_float_equal(self):
        self.assertEqual(merge_configs({"a": 1}, {"a": 1.0}), {"a": 1.0})
