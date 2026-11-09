import unittest

from solution import slugify


class SlugifyTests(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(slugify("Hello, World!"), "hello-world")

    def test_accents_are_removed(self):
        self.assertEqual(slugify("Café Déjà Vu"), "cafe-deja-vu")

    def test_compatibility_forms_are_decomposed(self):
        self.assertEqual(slugify("ﬁle ＡＢＣ ①"), "file-abc-1")

    def test_cjk_ideographs_are_kept_but_kana_is_not(self):
        self.assertEqual(slugify("东京 Tower 2026"), "东京-tower-2026")
        self.assertEqual(slugify("東京タワー"), "東京")

    def test_underscores_and_runs_collapse(self):
        self.assertEqual(slugify("__a__b--c  d__"), "a-b-c-d")

    def test_non_ascii_letters_without_decomposition_are_separators(self):
        self.assertEqual(slugify("straße"), "stra-e")

    def test_truncation_drops_trailing_hyphen(self):
        self.assertEqual(slugify("hello world", max_len=6), "hello")
        self.assertEqual(slugify("hello world", max_len=7), "hello-w")
        self.assertEqual(slugify("a" * 60), "a" * 50)

    def test_empty_result(self):
        self.assertEqual(slugify(""), "n-a")
        self.assertEqual(slugify("!!! ???"), "n-a")
        self.assertEqual(slugify("カタカナ"), "n-a")

    def test_bad_max_len(self):
        with self.assertRaises(ValueError):
            slugify("abc", max_len=0)


if __name__ == "__main__":
    unittest.main()
