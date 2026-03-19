"""Tests for gtd_tui/config.py — Config dataclass and load/save helpers."""

from __future__ import annotations

import tomllib
from pathlib import Path

from gtd_tui.config import Config, load_config, save_default_config

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


def test_save_default_config_creates_parent_dirs(tmp_path: Path) -> None:
    out = tmp_path / "nested" / "dir" / "config.toml"
    save_default_config(out)
    assert out.exists()
