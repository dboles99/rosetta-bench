import pytest

pytest.importorskip("rosetta_core.decision", reason="decision tests need rosetta-core installed")

from rosetta_bench.decision.masking import Masker


def test_emails_are_masked_consistently():
    masker = Masker()
    text = masker.mask_text("Mail ana@example.com, then ana@example.com again, cc bo@example.org")
    assert text == "Mail <email1>, then <email1> again, cc <email2>"
    assert set(masker.originals) == {"ana@example.com", "bo@example.org"}


def test_key_like_strings_are_masked():
    key = "sk-" + "a" * 24
    assert Masker().mask_text(f"use {key} please") == "use <secret1> please"


def test_long_phone_numbers_are_masked_but_dates_and_versions_are_not():
    masker = Masker()
    assert masker.mask_text("call +886 2 2345 6789") == "call <phone1>"
    assert masker.mask_text("released 2026-11-09 as 1.14.0") == "released 2026-11-09 as 1.14.0"


def test_extra_literals_are_masked_first():
    masker = Masker(extra_literals=("Dr Wei Chen",))
    assert masker.mask_text("Edit the paper by Dr Wei Chen") == "Edit the paper by <literal1>"


def test_nested_values_are_masked_and_non_strings_are_kept():
    masker = Masker()
    masked = masker.mask_value({"to": ["ana@example.com"], "n": 3, "ok": True})
    assert masked == {"to": ["<email1>"], "n": 3, "ok": True}
