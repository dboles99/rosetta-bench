import unittest

from solution import rle_encode, rle_decode


class RleTests(unittest.TestCase):
    def test_short_runs_stay_literal(self):
        self.assertEqual(rle_encode("aaab"), "aaab")
        self.assertEqual(rle_encode("abc"), "abc")

    def test_runs_of_four_or_more_are_encoded(self):
        self.assertEqual(rle_encode("aaaab"), "~a4;b")
        self.assertEqual(rle_encode("x" * 12), "~x12;")

    def test_tilde_always_uses_run_form(self):
        self.assertEqual(rle_encode("~"), "~~1;")
        self.assertEqual(rle_encode("a~~b"), "a~~2;b")

    def test_digit_runs(self):
        self.assertEqual(rle_encode("1111x"), "~14;x")
        self.assertEqual(rle_decode("~14;x"), "1111x")

    def test_unicode_code_points(self):
        self.assertEqual(rle_encode("日日日日本"), "~日4;本")

    def test_empty(self):
        self.assertEqual(rle_encode(""), "")
        self.assertEqual(rle_decode(""), "")

    def test_decode_literal_text(self):
        self.assertEqual(rle_decode("plain text 123"), "plain text 123")

    def test_decode_multi_digit_count(self):
        self.assertEqual(rle_decode("~a12;"), "a" * 12)

    def test_decode_errors(self):
        for bad in ("~a4", "~", "~a;", "~a04;", "~a0;", "x~", "~ab;"):
            with self.assertRaises(ValueError, msg=bad):
                rle_decode(bad)

    def test_round_trip(self):
        for text in ("", "~~~~~", "aaaa~bbbb1111", "zzz~zzzz;;;;", "日日日日~~12345555", "a;b;c~"):
            self.assertEqual(rle_decode(rle_encode(text)), text)


if __name__ == "__main__":
    unittest.main()
