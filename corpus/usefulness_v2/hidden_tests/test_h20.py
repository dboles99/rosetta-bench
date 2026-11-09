import unittest

from solution import TextBuffer


class TestTextBuffer(unittest.TestCase):
    def test_insert_and_delete(self):
        b = TextBuffer("hello")
        b.insert(5, " world")
        b.delete(0, 1)
        self.assertEqual(b.text, "ello world")

    def test_adjacent_inserts_merge_into_one_step(self):
        b = TextBuffer()
        b.insert(0, "ab")
        b.insert(2, "c")
        b.insert(3, "d")
        self.assertEqual(b.history_size(), 1)
        self.assertTrue(b.undo())
        self.assertEqual(b.text, "")
        self.assertTrue(b.redo())
        self.assertEqual(b.text, "abcd")

    def test_non_adjacent_insert_is_a_new_step(self):
        b = TextBuffer()
        b.insert(0, "ab")
        b.insert(0, "x")
        self.assertEqual(b.text, "xab")
        self.assertEqual(b.history_size(), 2)
        b.undo()
        self.assertEqual(b.text, "ab")

    def test_delete_breaks_merging(self):
        b = TextBuffer()
        b.insert(0, "ab")
        b.delete(1, 1)
        b.insert(1, "c")
        self.assertEqual(b.text, "ac")
        b.undo()
        self.assertEqual(b.text, "a")
        b.undo()
        self.assertEqual(b.text, "ab")
        b.undo()
        self.assertEqual(b.text, "")

    def test_undo_and_redo_break_merging(self):
        b = TextBuffer()
        b.insert(0, "a")
        b.undo()
        b.redo()
        b.insert(1, "b")
        b.undo()
        self.assertEqual(b.text, "a")

    def test_empty_edits_have_no_effect(self):
        b = TextBuffer()
        b.insert(0, "a")
        b.insert(1, "")
        b.delete(0, 0)
        b.insert(1, "b")
        self.assertEqual(b.history_size(), 1)
        b.undo()
        self.assertEqual(b.text, "")

    def test_empty_edit_keeps_redo(self):
        b = TextBuffer()
        b.insert(0, "a")
        b.undo()
        b.insert(0, "")
        b.delete(0, 0)
        self.assertTrue(b.redo())
        self.assertEqual(b.text, "a")

    def test_real_edit_clears_redo(self):
        b = TextBuffer()
        b.insert(0, "a")
        b.undo()
        b.insert(0, "b")
        self.assertFalse(b.redo())
        self.assertEqual(b.text, "b")

    def test_nothing_to_undo_or_redo(self):
        b = TextBuffer("x")
        self.assertFalse(b.undo())
        self.assertFalse(b.redo())
        self.assertEqual(b.text, "x")
        self.assertEqual(b.history_size(), 0)

    def test_index_errors_change_nothing(self):
        b = TextBuffer("abc")
        for call in (lambda: b.insert(4, "x"), lambda: b.insert(-1, "x"), lambda: b.delete(2, 2),
                     lambda: b.delete(-1, 1), lambda: b.delete(0, -1)):
            with self.assertRaises(IndexError):
                call()
        self.assertEqual(b.text, "abc")
        self.assertEqual(b.history_size(), 0)

    def test_failed_call_does_not_break_merging(self):
        b = TextBuffer()
        b.insert(0, "a")
        with self.assertRaises(IndexError):
            b.insert(5, "x")
        b.insert(1, "b")
        b.undo()
        self.assertEqual(b.text, "")

    def test_undo_delete_in_middle(self):
        b = TextBuffer("abcdef")
        b.delete(2, 2)
        self.assertEqual(b.text, "abef")
        b.undo()
        self.assertEqual(b.text, "abcdef")
        b.redo()
        self.assertEqual(b.text, "abef")


if __name__ == "__main__":
    unittest.main()
