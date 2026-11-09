import copy
import unittest

from solution import resolve, set_value, escape_token

DOC = {"a/b": 1, "m~n": 2, "": 3, "arr": [10, 20, {"k": "v"}], "~1": 5, "s": "text", "nested": {"x": {"y": None}}}


class TestResolve(unittest.TestCase):
    def test_whole_document(self):
        self.assertIs(resolve(DOC, ""), DOC)

    def test_escapes(self):
        self.assertEqual(resolve(DOC, "/a~1b"), 1)
        self.assertEqual(resolve(DOC, "/m~0n"), 2)

    def test_single_pass_decoding(self):
        self.assertEqual(resolve(DOC, "/~01"), 5)

    def test_slash_alone_is_empty_key(self):
        self.assertEqual(resolve(DOC, "/"), 3)

    def test_array_and_nested(self):
        self.assertEqual(resolve(DOC, "/arr/1"), 20)
        self.assertEqual(resolve(DOC, "/arr/2/k"), "v")
        self.assertIsNone(resolve(DOC, "/nested/x/y"))

    def test_lookup_failures_raise_key_error(self):
        for pointer in ("/missing", "/arr/01", "/arr/-", "/arr/3", "/arr/-1", "/arr/x", "/s/0", "/nested/x/y/z", "/arr/ 1"):
            with self.assertRaises(KeyError, msg=pointer):
                resolve(DOC, pointer)

    def test_malformed_pointers_raise_value_error(self):
        for pointer in ("a", "arr/0", "/x~2", "/x~", "/~"):
            with self.assertRaises(ValueError, msg=pointer):
                resolve(DOC, pointer)


class TestSetValue(unittest.TestCase):
    def setUp(self):
        self.doc = copy.deepcopy(DOC)
        self.snapshot = copy.deepcopy(DOC)

    def test_does_not_modify_input(self):
        new = set_value(self.doc, "/arr/2/k", "changed")
        self.assertEqual(new["arr"][2]["k"], "changed")
        self.assertEqual(self.doc, self.snapshot)
        self.assertIsNot(new["nested"], self.doc["nested"])

    def test_add_and_replace_dict_keys(self):
        self.assertEqual(set_value(self.doc, "/new", 1)["new"], 1)
        self.assertEqual(set_value(self.doc, "/a~1b", 9)["a/b"], 9)

    def test_list_replace_and_append(self):
        self.assertEqual(set_value(self.doc, "/arr/0", 99)["arr"], [99, 20, {"k": "v"}])
        self.assertEqual(set_value(self.doc, "/arr/-", 30)["arr"][-1], 30)
        self.assertEqual(set_value(self.doc, "/arr/3", 40)["arr"][3], 40)

    def test_list_index_beyond_length_raises(self):
        with self.assertRaises(KeyError):
            set_value(self.doc, "/arr/4", 0)
        with self.assertRaises(KeyError):
            set_value(self.doc, "/arr/01", 0)

    def test_missing_parent_raises(self):
        with self.assertRaises(KeyError):
            set_value(self.doc, "/nope/child", 1)
        with self.assertRaises(KeyError):
            set_value(self.doc, "/s/0", 1)

    def test_empty_pointer_returns_value(self):
        self.assertEqual(set_value(self.doc, "", [1, 2]), [1, 2])

    def test_malformed_pointer(self):
        with self.assertRaises(ValueError):
            set_value(self.doc, "new", 1)


class TestEscape(unittest.TestCase):
    def test_escape_order(self):
        self.assertEqual(escape_token("a/~b"), "a~1~0b")
        self.assertEqual(escape_token("~1"), "~01")

    def test_round_trip(self):
        for key in DOC:
            self.assertEqual(resolve(DOC, "/" + escape_token(key)), DOC[key])


if __name__ == "__main__":
    unittest.main()
