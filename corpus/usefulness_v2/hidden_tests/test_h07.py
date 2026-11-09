import unittest

from solution import wrap_text


class WrapTests(unittest.TestCase):
    def test_greedy_lines(self):
        self.assertEqual(wrap_text("the quick brown fox jumps over", 10), ["the quick", "brown fox", "jumps over"])

    def test_exact_fit(self):
        self.assertEqual(wrap_text("abcde fghij", 11), ["abcde fghij"])
        self.assertEqual(wrap_text("abcde fghij", 10), ["abcde", "fghij"])

    def test_word_of_exact_width_is_not_broken(self):
        self.assertEqual(wrap_text("abcde", 5), ["abcde"])

    def test_long_word_chunks_use_width_minus_one_plus_hyphen(self):
        self.assertEqual(wrap_text("abcdefgh", 5), ["abcd-", "efgh"])
        self.assertEqual(wrap_text("abcdefghi", 5), ["abcd-", "efghi"])
        self.assertEqual(wrap_text("abcdefghijklm", 5), ["abcd-", "efgh-", "ijklm"])

    def test_long_word_starts_a_new_line_even_with_room(self):
        self.assertEqual(wrap_text("ab abcdefgh", 5), ["ab", "abcd-", "efgh"])

    def test_words_can_follow_the_final_chunk(self):
        self.assertEqual(wrap_text("abcdefg x yz", 5), ["abcd-", "efg x", "yz"])

    def test_existing_hyphens_are_ordinary_characters(self):
        self.assertEqual(wrap_text("re-use it", 6), ["re-use", "it"])

    def test_any_whitespace_separates_words(self):
        self.assertEqual(wrap_text("one\ntwo\t\tthree\n\nfour", 9), ["one two", "three", "four"])

    def test_empty_and_blank_text(self):
        self.assertEqual(wrap_text("", 10), [])
        self.assertEqual(wrap_text("   \n ", 10), [])

    def test_width_two(self):
        self.assertEqual(wrap_text("abc", 2), ["a-", "bc"])

    def test_bad_width(self):
        for width in (1, 0, -3):
            with self.assertRaises(ValueError):
                wrap_text("abc", width)


if __name__ == "__main__":
    unittest.main()
