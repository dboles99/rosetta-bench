import time
import unittest
from solution import render


class TestRender(unittest.TestCase):
    def test_simple_and_spaces(self):
        self.assertEqual(render("Hi {{ name }}!", {"name": "Ann"}), "Hi Ann!")

    def test_dotted_lookup(self):
        self.assertEqual(render("{{user.address.city}}", {"user": {"address": {"city": "Taipei"}}}), "Taipei")

    def test_dotted_key_is_not_a_flat_key(self):
        with self.assertRaises(KeyError) as caught:
            render("{{a.b}}", {"a.b": 1})
        self.assertEqual(caught.exception.args[0], "missing: a.b")

    def test_fallback(self):
        self.assertEqual(render("[{{ x | n/a }}]", {}), "[n/a]")
        self.assertEqual(render("[{{x|}}]", {}), "[]")
        self.assertEqual(render("[{{x| a | b }}]", {}), "[a | b]")

    def test_none_is_missing(self):
        self.assertEqual(render("{{x|-}}", {"x": None}), "-")
        with self.assertRaises(KeyError):
            render("{{x}}", {"x": None})

    def test_intermediate_not_a_dict_is_missing(self):
        self.assertEqual(render("{{a.b|?}}", {"a": "text"}), "?")

    def test_formatting(self):
        self.assertEqual(render("{{t}} {{f}} {{n}} {{z}}", {"t": True, "f": False, "n": 3, "z": 0}), "true false 3 0")

    def test_escapes(self):
        self.assertEqual(render(r"\{{x}}", {"x": 1}), "{{x}}")
        self.assertEqual(render(r"\\{{x}}", {"x": 1}), "\\1")
        self.assertEqual(render(r"a\nb \} c\\d", {}), "a\\nb \\} c\\d")

    def test_lone_braces_are_literal(self):
        self.assertEqual(render("{a} }} { x }", {}), "{a} }} { x }")

    def test_values_are_not_rescanned(self):
        self.assertEqual(render("{{a}}", {"a": "{{b}}"}), "{{b}}")

    def test_unclosed(self):
        with self.assertRaisesRegex(ValueError, r"^unclosed placeholder at 4$"):
            render("abc {{x", {"x": 1})
        with self.assertRaisesRegex(ValueError, r"^unclosed placeholder at 9$"):
            render("{{x}} \\{{{{y", {"x": 1})

    def test_bad_key(self):
        for template, key in (("{{1x}}", "1x"), ("{{a..b}}", "a..b"), ("{{}}", ""), ("{{a b}}", "a b"), ("{{\tx}}", "\tx")):
            with self.subTest(template=template):
                with self.assertRaises(ValueError) as caught:
                    render(template, {"x": 1})
                self.assertEqual(str(caught.exception), f"bad key: {key}")

    def test_missing_message(self):
        with self.assertRaises(KeyError) as caught:
            render("{{ user.name }}", {"user": {}})
        self.assertEqual(caught.exception.args[0], "missing: user.name")


class TestPerformance(unittest.TestCase):
    def test_large_template(self):
        parts = []
        for i in range(200000):
            parts.append(f"row {i}: {{{{ item.v{i % 10} }}}} \\{{{{ ok }}}} ; ")
        template = "".join(parts)
        values = {"item": {f"v{k}": k for k in range(10)}}
        started = time.perf_counter()
        result = render(template, values)
        elapsed = time.perf_counter() - started
        self.assertTrue(result.startswith("row 0: 0 {{ ok }} ; row 1: 1 {{ ok }} ; "))
        self.assertEqual(result.count("{{ ok }}"), 200000)
        self.assertLess(elapsed, 4.0)
