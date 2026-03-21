"""Spell correction and capitalization fixes for user-entered text."""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

# Word tokens (letters and apostrophe inside words)
_TOKEN_RE = re.compile(r"[A-Za-z']+|[^A-Za-z']+")


def _fix_double_initial_caps_word(word: str) -> str:
    """e.g. THe -> The, HEllo -> Hello (first two letters upper, third lower)."""
    if len(word) < 3:
        return word
    if word[0].isupper() and word[1].isupper() and word[2].islower():
        return word[0] + word[1].lower() + word[2:]
    return word


def _fix_double_initial_caps_text(text: str) -> str:
    """Apply double-cap fix per alphabetic token."""
    parts = _TOKEN_RE.findall(text)
    out: list[str] = []
    for p in parts:
        if p and p[0].isalpha():
            out.append(_fix_double_initial_caps_word(p))
        else:
            out.append(p)
    return "".join(out)


def _apply_sentence_case(text: str) -> str:
    """Capitalize the first alphabetic character after . ! ? or start of string / newline."""
    result: list[str] = []
    capitalize_next = True
    for ch in text:
        if capitalize_next and ch.isalpha():
            result.append(ch.upper())
            capitalize_next = False
        else:
            result.append(ch)
        if ch in ".!?":
            capitalize_next = True
        elif ch == "\n":
            capitalize_next = True
    return "".join(result)


def fix_capitalization(text: str, *, sentence_case: bool = False) -> str:
    """Fix THe-style typos; optionally enforce sentence-style caps after punctuation."""
    if not text:
        return text
    fixed = _fix_double_initial_caps_text(text)
    if sentence_case:
        fixed = _apply_sentence_case(fixed)
    return fixed


@lru_cache(maxsize=1)
def _spell_checker() -> Any:
    from spellchecker import SpellChecker

    return SpellChecker()


def _fix_token_spell(token: str) -> str:
    """Correct a single alphabetic token; preserve original casing style when obvious."""
    if not token or not any(c.isalpha() for c in token):
        return token
    letters_only = "".join(c for c in token if c.isalpha())
    if not letters_only:
        return token
    sc: Any = _spell_checker()
    lower = letters_only.lower()
    if lower in sc:
        return token
    correction = sc.correction(lower)
    if not correction or correction == lower:
        return token
    # Preserve leading single upper (Title) vs all lower
    if letters_only[0].isupper() and letters_only[1:].islower():
        replacement = correction.capitalize()
    elif letters_only.islower():
        replacement = correction.lower()
    elif letters_only.isupper():
        replacement = correction.upper()
    else:
        replacement = correction
    # Re-attach non-alpha prefix/suffix (e.g. don't expect this path often)
    return replacement


def fix_spelling(text: str) -> str:
    """Replace unknown words with best-effort corrections (English dictionary)."""
    if not text:
        return text
    parts = _TOKEN_RE.findall(text)
    return "".join(_fix_token_spell(p) if p[:1].isalpha() else p for p in parts)
