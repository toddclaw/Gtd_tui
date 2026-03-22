"""Tests for spell and capitalization text processing."""

from __future__ import annotations

from gtd_tui.text.processing import fix_capitalization, fix_spelling


def test_fix_double_cap() -> None:
    assert fix_capitalization("THe quick") == "The quick"
    assert fix_capitalization("HEllo") == "Hello"


def test_fix_capitalization_sentence_case() -> None:
    out = fix_capitalization("hello. world", sentence_case=True)
    assert out.startswith("Hello")
    assert ". World" in out or out.endswith("World")


def test_fix_spelling_common_typo() -> None:
    assert "the" in fix_spelling("teh cat").lower()


def test_fix_spelling_preserves_known_word() -> None:
    assert fix_spelling("hello world") == "hello world"
