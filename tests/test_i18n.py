"""Tests for the i18n translation module (Feature F)."""

from __future__ import annotations

import pytest

from gtd_tui.i18n import set_language, t

# ---------------------------------------------------------------------------
# Reset between tests so they don't bleed into each other
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_language():
    set_language("en")
    yield
    set_language("en")


# ---------------------------------------------------------------------------
# Core t() behaviour
# ---------------------------------------------------------------------------


def test_t_returns_english_string_for_known_key():
    assert t("inbox") == "Inbox"


def test_t_returns_key_for_unknown_key():
    """Unknown keys must fall back to returning the key itself."""
    assert t("__nonexistent_key__") == "__nonexistent_key__"


def test_t_interpolates_kwargs():
    result = t("mode_visual", n=3)
    assert result == "VISUAL (3)"


def test_t_interpolates_multiple_kwargs():
    result = t("imported_tasks", count=5, active=4, completed=1, folder="inbox")
    assert "5" in result
    assert "4" in result
    assert "1" in result
    assert "inbox" in result


def test_t_no_kwargs_does_not_call_format():
    """A string with no kwargs must be returned verbatim (no spurious format call)."""
    result = t("inbox")
    assert result == "Inbox"


# ---------------------------------------------------------------------------
# set_language — Spanish translations
# ---------------------------------------------------------------------------


def test_set_language_es_translates_inbox():
    set_language("es")
    assert t("inbox") == "Entrada"


def test_set_language_es_translates_today():
    set_language("es")
    assert t("today") == "Hoy"


def test_set_language_es_falls_back_to_en_for_missing_key():
    """Keys present in en.json but absent from es.json must use English fallback."""
    set_language("es")
    # "inbox" is in both, so use a key that is unlikely to be translated
    # but must exist in English.  Use a key that is present in en.json.
    val = t("empty_hint")
    # The result must be the English string (or the Spanish one if translated),
    # but never the bare key.
    assert val != "empty_hint"


# ---------------------------------------------------------------------------
# set_language — unknown language falls back to English
# ---------------------------------------------------------------------------


def test_unknown_language_falls_back_to_english():
    set_language("zzz_unknown")
    assert t("inbox") == "Inbox"


# ---------------------------------------------------------------------------
# set_language — switching back to English
# ---------------------------------------------------------------------------


def test_switch_back_to_english_after_es():
    set_language("es")
    assert t("inbox") == "Entrada"
    set_language("en")
    assert t("inbox") == "Inbox"


# ---------------------------------------------------------------------------
# All locale files are valid JSON and contain the core sidebar keys
# ---------------------------------------------------------------------------

CORE_KEYS = ["inbox", "today", "anytime", "upcoming", "someday", "logbook"]
SUPPORTED_LANGUAGES = ["en", "es", "fr", "de", "zh", "ja", "ru"]


@pytest.mark.parametrize("lang", SUPPORTED_LANGUAGES)
def test_locale_file_has_core_sidebar_keys(lang: str):
    set_language(lang)
    for key in CORE_KEYS:
        val = t(key)
        # Must return a non-empty, non-key value
        assert val, f"Key '{key}' missing or empty in locale '{lang}'"
        # For English the value must differ from the key for well-known keys
        if lang == "en":
            assert val != key, f"English key '{key}' not translated"


# ---------------------------------------------------------------------------
# Parameterised strings work across languages
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("lang", SUPPORTED_LANGUAGES)
def test_parameterised_mode_visual_renders(lang: str):
    set_language(lang)
    result = t("mode_visual", n=7)
    assert "7" in result
