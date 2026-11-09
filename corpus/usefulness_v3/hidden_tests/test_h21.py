import re
import unittest

from solution import glob_to_regex, glob_match


class TestGlob(unittest.TestCase):
    def check(self, pattern, path, expected):
        self.assertIs(glob_match(pattern, path), expected, f"{pattern!r} vs {path!r}")

    def test_returns_regex_string(self):
        regex = glob_to_regex("*.py")
        self.assertIsInstance(regex, str)
        self.assertIsNotNone(re.fullmatch(regex, "a.py"))

    def test_star_stays_in_segment(self):
        self.check("*.py", "main.py", True)
        self.check("*.py", "src/main.py", False)
        self.check("*", "", True)

    def test_globstar_prefix(self):
        self.check("**/*.py", "main.py", True)
        self.check("**/*.py", "a/b/main.py", True)

    def test_globstar_middle(self):
        self.check("src/**/test_*.py", "src/test_a.py", True)
        self.check("src/**/test_*.py", "src/x/y/test_a.py", True)
        self.check("src/**/test_*.py", "srcx/test_a.py", False)

    def test_globstar_at_end(self):
        self.check("a/**", "a/b/c", True)
        self.check("a/**", "a/", True)
        self.check("a/**", "a", False)
        self.check("**", "x/y/z", True)

    def test_double_star_not_a_segment_is_single_star(self):
        self.check("a**b", "axxb", True)
        self.check("a**b", "ax/b", False)

    def test_three_stars_are_single_star(self):
        self.check("x/***", "x/y", True)
        self.check("x/***", "x/y/z", False)

    def test_question_mark(self):
        self.check("file?.txt", "file1.txt", True)
        self.check("file?.txt", "file10.txt", False)
        self.check("?", "/", False)

    def test_classes(self):
        self.check("[a-c]", "b", True)
        self.check("[a-c]", "d", False)
        self.check("[!a]x", "bx", True)
        self.check("[!a]x", "ax", False)

    def test_classes_never_match_slash(self):
        self.check("[!a]", "/", False)
        self.check("[/]", "/", False)
        self.check("a[!b]c", "a/c", False)

    def test_bracket_edge_cases(self):
        self.check("[]]", "]", True)
        self.check("[!]]", "a", True)
        self.check("[!]]", "]", False)
        self.check("[a-]", "-", True)
        self.check("[-a]", "-", True)
        self.check("[abc", "[abc", True)
        self.check("[abc", "a", False)

    def test_backslash_escapes(self):
        self.check("\\*", "*", True)
        self.check("\\*", "a", False)
        self.check("\\[a]", "[a]", True)
        self.check("a\\", "a\\", True)

    def test_regex_metacharacters_are_literal(self):
        self.check("a.b", "axb", False)
        self.check("a.b", "a.b", True)
        self.check("(x)+", "(x)+", True)
        self.check("$^|{1}", "$^|{1}", True)


if __name__ == "__main__":
    unittest.main()
