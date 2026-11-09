import unittest
from solution import word_count


class VisibleTests(unittest.TestCase):
    def test_counts(self):
        self.assertEqual(word_count("a b a"), {"a": 2, "b": 1})

    def test_joined(self):
        self.assertEqual(word_count(" ".join(["a", "b", "a"]))["a"], 1)

    def test_empty(self):
        self.assertEqual(word_count(""), {})
