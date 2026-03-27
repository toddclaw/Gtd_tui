"""Shared pytest fixtures for the gtd_tui test suite."""

from __future__ import annotations

import pytest

from gtd_tui.i18n import set_language


@pytest.fixture(autouse=True)
def reset_language() -> None:
    """Reset i18n to English before every test.

    Prevents the user's real config.toml (e.g. ``language = "zh"``) from
    bleeding into tests that create a ``GtdApp`` without pinning a config.
    Note: tests that create GtdApp with a config that has a non-English
    language will still use that language during the test run.
    """
    set_language("en")
    yield  # type: ignore[misc]
    set_language("en")
