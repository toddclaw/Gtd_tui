"""Configuration loading for gtd_tui.

Reads from ~/.config/gtd_tui/config.toml (XDG convention).
Returns a Config dataclass with sensible defaults when the file is absent
or cannot be parsed.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
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
class SidebarCountsConfig:
    """Controls which sidebar sections display item counts."""

    inbox: bool = True
    today: bool = True
    upcoming: bool = True
    waiting_on: bool = True
    someday: bool = True
    reference: bool = True
    logbook: bool = True
    user_folders: bool = True
    projects: bool = True
    tags: bool = True


@dataclass
class Config:
    """Application configuration.

    Attributes:
        timeout_minutes: Minutes of inactivity before auto-quit.
        timeout_enabled: Whether the auto-quit timeout is active.
        default_view: Sidebar view shown on launch ("today", "inbox", "upcoming",
            "someday", "waiting_on", or a user-folder id).
        theme: Color palette ("blue", "red", "yellow", "green").
        border_style: Screen border style ("none", "yellow_grey", "red_grey").
        border_block_size: Number of cells per color block in the border.
        counts: Controls which sidebar sections show item counts.
    """

    timeout_minutes: int = 30
    timeout_enabled: bool = True
    default_view: str = "today"
    theme: str = "blue"
    border_style: str = "none"
    border_block_size: int = 3
    counts: SidebarCountsConfig = field(default_factory=SidebarCountsConfig)


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
    ui_section = data.get("ui", {})
    counts_section = data.get("sidebar_counts", {})
    _def_counts = SidebarCountsConfig()
    counts = SidebarCountsConfig(
        inbox=bool(counts_section.get("inbox", _def_counts.inbox)),
        today=bool(counts_section.get("today", _def_counts.today)),
        upcoming=bool(counts_section.get("upcoming", _def_counts.upcoming)),
        waiting_on=bool(counts_section.get("waiting_on", _def_counts.waiting_on)),
        someday=bool(counts_section.get("someday", _def_counts.someday)),
        reference=bool(counts_section.get("reference", _def_counts.reference)),
        logbook=bool(counts_section.get("logbook", _def_counts.logbook)),
        user_folders=bool(counts_section.get("user_folders", _def_counts.user_folders)),
        projects=bool(counts_section.get("projects", _def_counts.projects)),
        tags=bool(counts_section.get("tags", _def_counts.tags)),
    )
    return Config(
        timeout_minutes=int(
            timeout_section.get("timeout_minutes", Config.timeout_minutes)
        ),
        timeout_enabled=bool(
            timeout_section.get("timeout_enabled", Config.timeout_enabled)
        ),
        default_view=str(ui_section.get("default_view", Config.default_view)),
        theme=str(ui_section.get("theme", Config.theme)),
        border_style=str(ui_section.get("border_style", Config.border_style)),
        border_block_size=int(
            ui_section.get("border_block_size", Config.border_block_size)
        ),
        counts=counts,
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

[ui]
# View shown when the app launches.
# Options: "today", "inbox", "upcoming", "waiting_on", "someday"
# (or the id of a user-created folder)
# default_view = "today"

# Color palette: "blue" | "red" | "yellow" | "green"
# theme = "blue"

# Screen border: "none" | "yellow_grey" | "red_grey"
# border_style = "none"

# Number of cells per color block in the border (when border_style != "none").
# border_block_size = 3

[sidebar_counts]
# Set any entry to false to hide counts for that section.
# inbox = true
# today = true
# upcoming = true
# waiting_on = true
# someday = true
# reference = true
# logbook = true
# user_folders = true
# projects = true
# tags = true
"""
    path.write_text(content)
