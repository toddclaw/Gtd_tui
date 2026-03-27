"""Tests for GtdApp.get_css_variables() — CSS variable injection.

Verifies that the variables returned by get_css_variables() are correct
for each theme / border_style combination so regressions are caught
without needing to visually inspect a running app.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from gtd_tui.app import GtdApp
from gtd_tui.config import Config


def _variables(tmp_path: Path, **cfg_fields: object) -> dict[str, str]:
    """Return get_css_variables() for a GtdApp built from Config() defaults
    with the given field overrides applied."""
    cfg = replace(Config(), **cfg_fields)
    data_file = tmp_path / "data.json"
    data_file.write_text('{"tasks": [], "areas": [], "folders": [], "projects": []}')
    app = GtdApp(data_file=data_file, config=cfg)
    return app.get_css_variables()


# ---------------------------------------------------------------------------
# $gtd-modal-border — border_style variants
# ---------------------------------------------------------------------------


def test_default_border_style_none_uses_primary(tmp_path: Path) -> None:
    """With border_style='none' (default), $gtd-modal-border equals $primary."""
    vars_ = _variables(tmp_path)
    assert vars_["gtd-modal-border"] == vars_["primary"]


def test_red_grey_border_style_sets_red(tmp_path: Path) -> None:
    """border_style=red_grey sets $gtd-modal-border to the red theme hex."""
    vars_ = _variables(tmp_path, border_style="red_grey")
    assert vars_["gtd-modal-border"] == "#C0392B"


def test_yellow_grey_border_style_sets_yellow(tmp_path: Path) -> None:
    """border_style=yellow_grey sets $gtd-modal-border to the yellow theme hex."""
    vars_ = _variables(tmp_path, border_style="yellow_grey")
    assert vars_["gtd-modal-border"] == "#D4A017"


def test_unknown_border_style_falls_back_to_primary(tmp_path: Path) -> None:
    """An unrecognised border_style still produces $gtd-modal-border == $primary."""
    vars_ = _variables(tmp_path, border_style="solid")
    assert vars_["gtd-modal-border"] == vars_["primary"]


# ---------------------------------------------------------------------------
# Theme-derived $primary overrides
# ---------------------------------------------------------------------------


def test_blue_theme_default_primary(tmp_path: Path) -> None:
    """Blue (default) theme uses the built-in Textual blue primary."""
    vars_ = _variables(tmp_path, theme="blue")
    # Textual may round hex values slightly; check the hue is in the blue family
    # by confirming it differs from the red/yellow/green palettes.
    assert vars_["primary"] not in ("#C0392B", "#D4A017", "#1E8A3E")


def test_red_theme_overrides_primary(tmp_path: Path) -> None:
    """Red theme overrides $primary away from the default blue."""
    blue_vars = _variables(tmp_path, theme="blue")
    red_vars = _variables(tmp_path, theme="red")
    assert red_vars["primary"] != blue_vars["primary"]


def test_yellow_theme_overrides_primary(tmp_path: Path) -> None:
    """Yellow theme overrides $primary away from the default blue."""
    blue_vars = _variables(tmp_path, theme="blue")
    yellow_vars = _variables(tmp_path, theme="yellow")
    assert yellow_vars["primary"] != blue_vars["primary"]


def test_green_theme_overrides_primary(tmp_path: Path) -> None:
    """Green theme overrides $primary away from the default blue."""
    blue_vars = _variables(tmp_path, theme="blue")
    green_vars = _variables(tmp_path, theme="green")
    assert green_vars["primary"] != blue_vars["primary"]


# ---------------------------------------------------------------------------
# Interaction: border_style overrides theme for modal border
# ---------------------------------------------------------------------------


def test_red_grey_border_overrides_blue_theme_modal_border(tmp_path: Path) -> None:
    """border_style=red_grey gives red modal borders even when theme=blue."""
    vars_ = _variables(tmp_path, theme="blue", border_style="red_grey")
    assert vars_["gtd-modal-border"] == "#C0392B"
    # Modal border is explicitly red, not the default blue primary
    assert vars_["gtd-modal-border"] != vars_["primary"]


def test_yellow_grey_border_overrides_green_theme_modal_border(tmp_path: Path) -> None:
    """border_style=yellow_grey gives yellow modal borders even when theme=green."""
    vars_ = _variables(tmp_path, theme="green", border_style="yellow_grey")
    assert vars_["gtd-modal-border"] == "#D4A017"


def test_red_grey_border_on_red_theme_gives_red(tmp_path: Path) -> None:
    """When theme=red and border_style=red_grey, modal border is the red hex."""
    vars_ = _variables(tmp_path, theme="red", border_style="red_grey")
    assert vars_["gtd-modal-border"] == "#C0392B"


def test_default_border_on_red_theme_uses_theme_primary(tmp_path: Path) -> None:
    """With theme=red and default border_style, modal border tracks $primary."""
    vars_ = _variables(tmp_path, theme="red")
    assert vars_["gtd-modal-border"] == vars_["primary"]


def test_gtd_modal_border_always_present(tmp_path: Path) -> None:
    """$gtd-modal-border is always set regardless of config combination."""
    for theme in ("blue", "red", "yellow", "green"):
        for bs in ("none", "red_grey", "yellow_grey", "solid"):
            vars_ = _variables(tmp_path, theme=theme, border_style=bs)
            assert (
                "gtd-modal-border" in vars_
            ), f"gtd-modal-border missing for theme={theme}, border_style={bs}"
