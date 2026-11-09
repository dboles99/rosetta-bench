import unittest

from solution import parse_csv_line, format_csv_line


class TestParse(unittest.TestCase):
    def test_plain_fields(self):
        self.assertEqual(parse_csv_line("a,b,c"), ["a", "b", "c"])

    def test_quoted_field_with_delimiter(self):
        self.assertEqual(parse_csv_line('a,"b,c",d'), ["a", "b,c", "d"])

    def test_doubled_quotes(self):
        self.assertEqual(parse_csv_line('"he said ""hi"""'), ['he said "hi"'])

    def test_leading_space_means_unquoted(self):
        self.assertEqual(parse_csv_line(' "a",b'), [' "a"', "b"])

    def test_quote_inside_unquoted_field_is_literal(self):
        self.assertEqual(parse_csv_line('a"b,c'), ['a"b', "c"])

    def test_whitespace_preserved(self):
        self.assertEqual(parse_csv_line(" a , b "), [" a ", " b "])

    def test_text_after_closing_quote_raises(self):
        with self.assertRaises(ValueError):
            parse_csv_line('"a"x,b')

    def test_unterminated_quote_raises(self):
        for bad in ('"abc', 'a,"b', '"a""'):
            with self.assertRaises(ValueError, msg=bad):
                parse_csv_line(bad)

    def test_empty_line_is_one_empty_field(self):
        self.assertEqual(parse_csv_line(""), [""])

    def test_trailing_delimiter_adds_empty_field(self):
        self.assertEqual(parse_csv_line("a,"), ["a", ""])
        self.assertEqual(parse_csv_line(",,"), ["", "", ""])

    def test_empty_quoted_fields(self):
        self.assertEqual(parse_csv_line('""'), [""])
        self.assertEqual(parse_csv_line('"",""'), ["", ""])

    def test_custom_delimiter_and_quote(self):
        self.assertEqual(parse_csv_line("a;b,c", delimiter=";"), ["a", "b,c"])
        self.assertEqual(parse_csv_line("'x;y';z", delimiter=";", quote="'"), ["x;y", "z"])

    def test_newline_inside_quotes(self):
        self.assertEqual(parse_csv_line('"x\ny",z'), ["x\ny", "z"])


class TestFormat(unittest.TestCase):
    def test_quoting_rules(self):
        fields = ["a", "b,c", 'he "x"', " lead", "trail ", ""]
        self.assertEqual(format_csv_line(fields), 'a,"b,c","he ""x"""," lead","trail ",')

    def test_custom_delimiter(self):
        self.assertEqual(format_csv_line(["a;b", "c,d"], delimiter=";"), '"a;b";c,d')

    def test_newlines_are_quoted(self):
        self.assertEqual(format_csv_line(["x\ny", "p\rq"]), '"x\ny","p\rq"')

    def test_round_trip(self):
        for fields in (["a", "b"], ["", ""], ['"', ",", " "], ["one"], ["a b", 'q"q', "x,y,z"]):
            self.assertEqual(parse_csv_line(format_csv_line(fields)), fields)


if __name__ == "__main__":
    unittest.main()
