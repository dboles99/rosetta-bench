import unittest

from solution import encode_id, decode_id


class CrockfordTests(unittest.TestCase):
    def test_encode_known_values(self):
        self.assertEqual(encode_id(0), "00")
        self.assertEqual(encode_id(1), "11")
        self.assertEqual(encode_id(31), "ZZ")
        self.assertEqual(encode_id(32), "10*")
        self.assertEqual(encode_id(36), "14U")
        self.assertEqual(encode_id(1234), "16JD")

    def test_check_symbol_uses_mod_37(self):
        self.assertEqual(encode_id(33), "11~")
        self.assertEqual(encode_id(34), "12$")
        self.assertEqual(encode_id(35), "13=")
        self.assertEqual(encode_id(37), "150")

    def test_encode_errors(self):
        with self.assertRaises(ValueError):
            encode_id(-1)
        for bad in (True, 1.0, "5"):
            with self.assertRaises(TypeError):
                encode_id(bad)

    def test_round_trip(self):
        for n in list(range(0, 2000)) + [2 ** 40 + 12345, 10 ** 18]:
            self.assertEqual(decode_id(encode_id(n)), n)

    def test_decode_is_case_insensitive_and_ignores_hyphens(self):
        self.assertEqual(decode_id("16jd"), 1234)
        self.assertEqual(decode_id("1-6-J-D"), 1234)
        self.assertEqual(decode_id("14u"), 36)

    def test_decode_aliases(self):
        self.assertEqual(decode_id("I1"), 1)
        self.assertEqual(decode_id("l1"), 1)
        self.assertEqual(decode_id("O0"), 0)
        self.assertEqual(decode_id("1O*"), 32)
        self.assertEqual(decode_id("1i"), 1)

    def test_leading_zeros_allowed(self):
        self.assertEqual(decode_id("0016JD"), 1234)

    def test_checksum_mismatch(self):
        with self.assertRaises(ValueError) as ctx:
            decode_id("16JE")
        self.assertTrue(str(ctx.exception).startswith("checksum"), str(ctx.exception))

    def test_invalid_symbols(self):
        for bad in ("", "-", "1", "U1", "*0", "1U0", "1!", "1~0", "A B"):
            with self.assertRaises(ValueError, msg=bad):
                decode_id(bad)


if __name__ == "__main__":
    unittest.main()
