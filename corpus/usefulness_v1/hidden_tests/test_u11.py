import unittest
from solution import bullet_count


class AcceptanceTests(unittest.TestCase):
    def test_kinds(self):
        self.assertEqual(bullet_count("- a\n* b\n3. c\n\u2022 d\n"), 4)
    def test_requires_space(self):
        self.assertEqual(bullet_count("-no space\n"), 0)
    def test_indented_paren(self):
        self.assertEqual(bullet_count("  1) x\nplain text\n"), 1)
