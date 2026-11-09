import copy
import unittest

from solution import diff_events, merge_streams, validate_stream


class TestValidate(unittest.TestCase):
    def test_valid_returns_none(self):
        self.assertIsNone(validate_stream([(1, "a", 0), (1, "b", 0), (2, "a2", 0)]))
        self.assertIsNone(validate_stream([]))

    def test_duplicate_checked_first(self):
        for events in ([(1, "a", 0), (1, "a", 0)], [(2, "a", 0), (1, "a", 0)], [(1, "a", 0), (2, "a", 1)]):
            with self.assertRaises(ValueError) as ctx:
                validate_stream(events)
            self.assertTrue(str(ctx.exception).startswith("duplicate id"), str(ctx.exception))

    def test_unsorted(self):
        for events in ([(2, "a", 0), (1, "b", 0)], [(1, "b", 0), (1, "a", 0)]):
            with self.assertRaises(ValueError) as ctx:
                validate_stream(events)
            self.assertTrue(str(ctx.exception).startswith("unsorted"), str(ctx.exception))


class TestDiff(unittest.TestCase):
    def test_all_categories(self):
        old = [(1, "a", {"v": 1}), (2, "b", {"v": 2}), (3, "c", {"v": 3}), (4, "d", 0)]
        new = [(1, "a", {"v": 1}), (2, "e", 0), (3, "c", {"v": 30}), (5, "b", {"v": 2}), (6, "f", 0)]
        self.assertEqual(diff_events(old, new), {"added": ["e", "f"], "removed": ["d"], "moved": ["b"], "changed": ["c"]})

    def test_moved_and_changed_follow_new_order(self):
        old = [(1, "x", 0), (2, "y", 0)]
        new = [(5, "y", 1), (6, "x", 1)]
        result = diff_events(old, new)
        self.assertEqual(result["moved"], ["y", "x"])
        self.assertEqual(result["changed"], ["y", "x"])
        self.assertEqual(result["added"], [])
        self.assertEqual(result["removed"], [])

    def test_removed_follows_old_order(self):
        old = [(1, "q", 0), (2, "p", 0), (3, "r", 0)]
        self.assertEqual(diff_events(old, [(3, "r", 0)])["removed"], ["q", "p"])

    def test_exact_keys(self):
        self.assertEqual(set(diff_events([], [])), {"added", "removed", "moved", "changed"})

    def test_validates_old_then_new(self):
        with self.assertRaises(ValueError) as ctx:
            diff_events([(1, "a", 0), (1, "a", 0)], [(2, "a", 0), (1, "b", 0)])
        self.assertTrue(str(ctx.exception).startswith("duplicate id"))
        with self.assertRaises(ValueError) as ctx:
            diff_events([(1, "a", 0)], [(2, "a", 0), (1, "b", 0)])
        self.assertTrue(str(ctx.exception).startswith("unsorted"))


class TestMerge(unittest.TestCase):
    def test_b_wins_and_result_is_sorted(self):
        a = [(1, "a", 0), (3, "c", 0)]
        b = [(2, "b", 0), (4, "a", 9)]
        self.assertEqual(merge_streams(a, b), [(2, "b", 0), (3, "c", 0), (4, "a", 9)])

    def test_same_timestamp_ordered_by_id(self):
        self.assertEqual(merge_streams([(1, "b", 0)], [(1, "a", 0)]), [(1, "a", 0), (1, "b", 0)])

    def test_unhashable_payloads_and_inputs_unchanged(self):
        a = [(1, "a", {"k": [1]}), (2, "b", {"k": [2]})]
        b = [(2, "b", {"k": [3]})]
        a_copy, b_copy = copy.deepcopy(a), copy.deepcopy(b)
        self.assertEqual(merge_streams(a, b), [(1, "a", {"k": [1]}), (2, "b", {"k": [3]})])
        self.assertEqual(diff_events(a, b)["changed"], ["b"])
        self.assertEqual((a, b), (a_copy, b_copy))

    def test_empty(self):
        self.assertEqual(merge_streams([], []), [])

    def test_validates(self):
        with self.assertRaises(ValueError):
            merge_streams([(2, "a", 0), (1, "b", 0)], [])


if __name__ == "__main__":
    unittest.main()
