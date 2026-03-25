"""Internationalization (i18n) support for gtd_tui.

Usage::

    from gtd_tui.i18n import set_language, t

    set_language("es")          # load Spanish translations
    print(t("inbox"))           # → "Entrada"
    print(t("imported_tasks", count=3, completed=1, folder="inbox"))

Locale files live in ``gtd_tui/i18n/locales/<lang>.json``.
English (``en``) is the canonical source and is always used as fallback.
"""

from __future__ import annotations

import json
from pathlib import Path

_translations: dict[str, str] = {}
_fallback: dict[str, str] = {}


def set_language(lang: str) -> None:
    """Load the requested locale, with English as fallback.

    Args:
        lang: BCP-47 language tag without region suffix (e.g. ``"en"``, ``"es"``).
              Unknown languages silently fall back to English.
    """
    global _translations, _fallback
    _fallback = _load("en")
    _translations = _load(lang) if lang != "en" else _fallback


def _load(lang: str) -> dict[str, str]:
    """Load a locale file and return its key→string mapping (empty dict if absent)."""
    path = Path(__file__).parent / "locales" / f"{lang}.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def t(key: str, **kwargs: object) -> str:
    """Return the translated string for *key*, falling back to English then to *key*.

    Keyword arguments are interpolated using Python :meth:`str.format`.

    Examples::

        t("inbox")                                       # → "Inbox"
        t("imported_tasks", count=3, completed=1, folder="inbox")
    """
    text = _translations.get(key) or _fallback.get(key, key)
    return text.format(**kwargs) if kwargs else text


__all__ = ["set_language", "t"]
