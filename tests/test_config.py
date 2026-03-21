"""Tests for gtd_tui/config.py — Config dataclass and load/save helpers."""

from __future__ import annotations

import tomllib
from pathlib import Path

from gtd_tui.config import (
    Config,
    _ensure_config_defaults,
    load_config,
    save_default_config,
)

# ---------------------------------------------------------------------------
# Config dataclass defaults
# ---------------------------------------------------------------------------


def test_config_default_timeout_minutes() -> None:
    cfg = Config()
    assert cfg.timeout_minutes == 30


def test_config_default_timeout_enabled() -> None:
    cfg = Config()
    assert cfg.timeout_enabled is True


def test_config_custom_values() -> None:
    cfg = Config(timeout_minutes=15, timeout_enabled=False)
    assert cfg.timeout_minutes == 15
    assert cfg.timeout_enabled is False


# ---------------------------------------------------------------------------
# load_config
# ---------------------------------------------------------------------------


def test_load_config_returns_defaults_when_file_missing(tmp_path: Path) -> None:
    cfg = load_config(tmp_path / "nonexistent.toml")
    assert cfg.timeout_minutes == 30
    assert cfg.timeout_enabled is True


def test_load_config_reads_values_from_toml(tmp_path: Path) -> None:
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text("[timeout]\ntimeout_minutes = 45\ntimeout_enabled = false\n")
    cfg = load_config(cfg_file)
    assert cfg.timeout_minutes == 45
    assert cfg.timeout_enabled is False


def test_load_config_partial_toml_uses_defaults_for_missing_keys(
    tmp_path: Path,
) -> None:
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text("[timeout]\ntimeout_minutes = 10\n")
    cfg = load_config(cfg_file)
    assert cfg.timeout_minutes == 10
    assert cfg.timeout_enabled is True  # default


def test_load_config_returns_defaults_on_corrupt_toml(tmp_path: Path) -> None:
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text("this is not valid toml ][[[")
    cfg = load_config(cfg_file)
    assert cfg.timeout_minutes == 30
    assert cfg.timeout_enabled is True


def test_load_config_no_path_returns_defaults() -> None:
    cfg = load_config(None)
    assert cfg.timeout_minutes == 30
    assert cfg.timeout_enabled is True


# ---------------------------------------------------------------------------
# save_default_config
# ---------------------------------------------------------------------------


def test_save_default_config_creates_file(tmp_path: Path) -> None:
    out = tmp_path / "config.toml"
    save_default_config(out)
    assert out.exists()


def test_save_default_config_is_valid_toml(tmp_path: Path) -> None:
    out = tmp_path / "config.toml"
    save_default_config(out)
    with open(out, "rb") as f:
        data = tomllib.load(f)
    assert isinstance(data, dict)


def test_save_default_config_contains_timeout_section(tmp_path: Path) -> None:
    out = tmp_path / "config.toml"
    save_default_config(out)
    with open(out, "rb") as f:
        data = tomllib.load(f)
    assert "timeout" in data


def test_save_default_config_contains_backup_and_text_sections(tmp_path: Path) -> None:
    out = tmp_path / "config.toml"
    save_default_config(out)
    with open(out, "rb") as f:
        data = tomllib.load(f)
    assert "backup" in data
    assert data["backup"]["enabled"] is False
    assert "text" in data
    assert data["text"]["spell_check_enabled"] is False


def test_load_config_reads_backup_and_text(tmp_path: Path) -> None:
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text(
        "[backup]\nenabled = true\ndaily_keep = 3\nthrottle_minutes = 0\n"
        "[text]\nspell_check_enabled = true\ncapitalization_fix_enabled = true\n"
    )
    cfg = load_config(cfg_file)
    assert cfg.backup.enabled is True
    assert cfg.backup.daily_keep == 3
    assert cfg.text.spell_check_enabled is True
    assert cfg.text.capitalization_fix_enabled is True


def test_save_default_config_contains_startup_focus_sidebar(tmp_path: Path) -> None:
    """Fresh default config includes startup_focus_sidebar in [ui] section."""
    out = tmp_path / "config.toml"
    save_default_config(out)
    with open(out, "rb") as f:
        data = tomllib.load(f)
    assert "ui" in data
    assert "startup_focus_sidebar" in data["ui"]
    assert data["ui"]["startup_focus_sidebar"] is True


def test_ensure_config_defaults_adds_startup_focus_sidebar_when_missing(
    tmp_path: Path,
) -> None:
    """Old config without startup_focus_sidebar gets it appended by _ensure_config_defaults."""
    cfg = tmp_path / "config.toml"
    cfg.write_text('[timeout]\ntimeout_minutes = 30\n\n[ui]\ndefault_view = "today"\n')
    raw = tomllib.loads(cfg.read_text())
    _ensure_config_defaults(cfg, raw)
    data = tomllib.loads(cfg.read_text())
    assert "startup_focus_sidebar" in data.get("ui", {})
    assert data["ui"]["startup_focus_sidebar"] is True


def test_save_default_config_creates_parent_dirs(tmp_path: Path) -> None:
    out = tmp_path / "nested" / "dir" / "config.toml"
    save_default_config(out)
    assert out.exists()


# ---------------------------------------------------------------------------
# default_view config setting
# ---------------------------------------------------------------------------


def test_config_default_view_default() -> None:
    cfg = Config()
    assert cfg.default_view == "today"


def test_load_config_reads_default_view(tmp_path: Path) -> None:
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text('[ui]\ndefault_view = "inbox"\n')
    cfg = load_config(cfg_file)
    assert cfg.default_view == "inbox"


def test_load_config_missing_default_view_uses_default(tmp_path: Path) -> None:
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text("[timeout]\ntimeout_minutes = 10\n")
    cfg = load_config(cfg_file)
    assert cfg.default_view == "today"


# ---------------------------------------------------------------------------
# Regression: _ensure_config_defaults must not re-add keys that are commented
# ---------------------------------------------------------------------------


def test_ensure_config_defaults_skips_commented_keys(tmp_path: Path) -> None:
    """_ensure_config_defaults should not append keys that appear as comments."""
    cfg = tmp_path / "config.toml"
    # Write a config where some keys are present only as comments
    cfg.write_text(
        "[timeout]\n"
        "timeout_minutes = 60\n"
        "# timeout_enabled = false\n"
        "\n[ui]\n"
        '# default_view = "inbox"\n'
        'theme = "red"\n'
    )
    raw = tomllib.loads(cfg.read_text())
    _ensure_config_defaults(cfg, raw)

    text_after = cfg.read_text()
    # timeout_enabled and default_view appear as comments — they must NOT be appended again
    assert text_after.count("timeout_enabled") == 1
    assert text_after.count("default_view") == 1
