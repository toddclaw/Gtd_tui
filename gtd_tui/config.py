"""Configuration loading for gtd_tui.

Reads from ~/.config/gtd_tui/config.toml (XDG convention).
Returns a Config dataclass with sensible defaults when the file is absent
or cannot be parsed.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

try:
    from platformdirs import user_config_dir
except ImportError:  # pragma: no cover — should always be available

    def user_config_dir(app: str) -> str:  # type: ignore[misc]
        return str(Path.home() / ".config" / app)


def default_config_path() -> Path:
    """Return the XDG-standard path for the config file."""
    return Path(user_config_dir("gtd_tui")) / "config.toml"


def _default_config_path() -> Path:  # internal alias kept for backward compat
    return default_config_path()


@dataclass
class Config:
    """Application configuration.

    Attributes:
        timeout_minutes: Minutes of inactivity before auto-quit.
        timeout_enabled: Whether the auto-quit timeout is active.
    """

    timeout_minutes: int = 30
    timeout_enabled: bool = True


def load_config(path: Path | None = None) -> Config:
    """Load configuration from *path*, returning defaults on any error.

    Args:
        path: Path to a TOML config file.  When None the XDG default location
              is used.  Returns defaults when the file is missing or corrupt.
    """
    cfg_path = path if path is not None else _default_config_path()
    try:
        with open(cfg_path, "rb") as fh:
            data = tomllib.load(fh)
    except (FileNotFoundError, tomllib.TOMLDecodeError, OSError):
        return Config()

    timeout_section = data.get("timeout", {})
    return Config(
        timeout_minutes=int(
            timeout_section.get("timeout_minutes", Config.timeout_minutes)
        ),
        timeout_enabled=bool(
            timeout_section.get("timeout_enabled", Config.timeout_enabled)
        ),
    )


def save_default_config(path: Path) -> None:
    """Write a commented default config file to *path*.

    Creates parent directories as needed.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    content = """\
# gtd_tui configuration
# Generated automatically — edit as needed.

[timeout]
# Auto-quit after this many minutes of inactivity.
timeout_minutes = 30

# Set to false to disable the inactivity timeout entirely.
timeout_enabled = true
"""
    path.write_text(content)
