import unicodedata
import unittest
from solution import count_chars


class VisibleTests(unittest.TestCase):
    def test_precomposed(self):
        self.assertEqual(count_chars("\u00e9t\u00e9"), 3)

    def test_normalized(self):
        self.assertEqual(count_chars(unicodedata.normalize("NFC", "e\u0301te\u0301")), 5)

    def test_ascii(self):
        self.assertEqual(count_chars("abc"), 3)
