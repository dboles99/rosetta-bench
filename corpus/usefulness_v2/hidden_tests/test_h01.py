import unittest

from solution import parse_ini


class ParseIniTests(unittest.TestCase):
    def test_sections_and_keys_are_lowercased_and_stripped(self):
        text = "[ Server ]\nHost =  example.org  \nPORT=8080\n"
        self.assertEqual(parse_ini(text), {"server": {"host": "example.org", "port": "8080"}})

    def test_inline_comment_text_is_kept(self):
        self.assertEqual(parse_ini("[a]\nx = 1 ; not a comment\n"), {"a": {"x": "1 ; not a comment"}})

    def test_split_at_first_equals_only(self):
        self.assertEqual(parse_ini("[a]\nurl = http://h/?q=1&r=2\n"), {"a": {"url": "http://h/?q=1&r=2"}})

    def test_continuation_lines_join_with_single_space(self):
        text = "[a]\nmsg = hello\n    big\n\tworld\nnext = 2\n"
        self.assertEqual(parse_ini(text), {"a": {"msg": "hello big world", "next": "2"}})

    def test_continuation_onto_empty_value(self):
        self.assertEqual(parse_ini("[a]\nk =\n   value\n"), {"a": {"k": "value"}})

    def test_comment_lines_do_not_end_a_continuation(self):
        text = "[a]\nk = one\n# note\n  two\n"
        self.assertEqual(parse_ini(text), {"a": {"k": "one two"}})

    def test_indented_comment_is_a_comment(self):
        self.assertEqual(parse_ini("[a]\nk = v\n    ; indented comment\n"), {"a": {"k": "v"}})

    def test_blank_line_ends_continuation_and_then_indent_is_an_error(self):
        with self.assertRaises(ValueError) as ctx:
            parse_ini("[a]\nk = v\n\n  orphan\n")
        self.assertTrue(str(ctx.exception).startswith("line 4:"), str(ctx.exception))

    def test_indented_line_after_header_is_an_error(self):
        with self.assertRaises(ValueError) as ctx:
            parse_ini("[a]\n  x = 1\n")
        self.assertTrue(str(ctx.exception).startswith("line 2:"), str(ctx.exception))

    def test_repeated_sections_merge(self):
        text = "[a]\nx=1\n[b]\ny=2\n[A]\nz=3\n"
        self.assertEqual(parse_ini(text), {"a": {"x": "1", "z": "3"}, "b": {"y": "2"}})

    def test_duplicate_key_across_repeated_section_raises(self):
        with self.assertRaises(ValueError) as ctx:
            parse_ini("[a]\nx=1\n[b]\n[a]\nX=2\n")
        self.assertTrue(str(ctx.exception).startswith("duplicate key"), str(ctx.exception))

    def test_keys_before_any_section_go_to_empty_section(self):
        self.assertEqual(parse_ini("top = 1\n[s]\nk = 2\n"), {"": {"top": "1"}, "s": {"k": "2"}})

    def test_quoted_values_lose_one_pair_of_quotes(self):
        text = '[a]\np = "  padded  "\nq = "\nr = ""\n'
        self.assertEqual(parse_ini(text), {"a": {"p": "  padded  ", "q": '"', "r": ""}})

    def test_empty_text_and_empty_section(self):
        self.assertEqual(parse_ini(""), {})
        self.assertEqual(parse_ini("[empty]\n"), {"empty": {}})

    def test_line_without_equals_reports_its_line_number(self):
        with self.assertRaises(ValueError) as ctx:
            parse_ini("[a]\njust words\n")
        self.assertTrue(str(ctx.exception).startswith("line 2:"), str(ctx.exception))

    def test_crlf_line_endings(self):
        self.assertEqual(parse_ini("[a]\r\nk = v\r\n  w\r\n"), {"a": {"k": "v w"}})


if __name__ == "__main__":
    unittest.main()
