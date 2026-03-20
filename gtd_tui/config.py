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
        startup_focus_sidebar: If True, focus sidebar on launch; if False, focus
            task list (legacy behavior, used by tests).
        theme: Color palette ("blue", "red", "yellow", "green").
        border_style: Screen border style ("none", "yellow_grey", "red_grey").
        border_block_size: Number of cells per color block in the border.
        border_text: Optional text label rendered inside the screen border.
        counts: Controls which sidebar sections show item counts.
    """

    timeout_minutes: int = 30
    timeout_enabled: bool = True
    default_view: str = "today"
    startup_focus_sidebar: bool = True
    theme: str = "blue"
    border_style: str = "none"
    border_block_size: int = 3
    border_text: str = ""
    counts: SidebarCountsConfig = field(default_factory=SidebarCountsConfig)


def _ensure_config_defaults(path: Path, raw: dict) -> None:
    """Append any missing default config keys to an existing config file.

    Checks both active and commented keys — if a key appears in any form
    (active or commented), it is considered "present" and won't be appended.
    Non-destructive: only appends content, never modifies existing lines.
    Silently ignores write errors (e.g. read-only file).
    """
    import re as _re

    try:
        file_text = path.read_text(encoding="utf-8")
    except OSError:
        return

    def _has_key(key: str) -> bool:
        """Return True if key appears anywhere in file (active OR commented)."""
        return bool(_re.search(rf"(?m)^\s*#?\s*{_re.escape(key)}\s*=", file_text))

    missing: list[str] = []

    # [timeout] section
    timeout_lines: list[str] = []
    if not _has_key("timeout_minutes"):
        timeout_lines.append("timeout_minutes = 30\n")
    if not _has_key("timeout_enabled"):
        timeout_lines.append("timeout_enabled = true\n")
    if timeout_lines:
        if "timeout" not in raw:
            missing.append("\n[timeout]\n")
        missing.extend(timeout_lines)

    # [ui] section
    ui_lines: list[str] = []
    if not _has_key("default_view"):
        ui_lines.append('default_view = "today"\n')
    if not _has_key("theme"):
        ui_lines.append('theme = "blue"\n')
    if not _has_key("border_style"):
        ui_lines.append('border_style = "none"\n')
    if not _has_key("border_block_size"):
        ui_lines.append("border_block_size = 3\n")
    if not _has_key("border_text"):
        ui_lines.append('border_text = ""\n')
    if ui_lines:
        if "ui" not in raw:
            missing.append("\n[ui]\n")
        missing.extend(ui_lines)

    # [sidebar_counts] section
    count_keys = [
        "inbox",
        "today",
        "upcoming",
        "waiting_on",
        "someday",
        "reference",
        "logbook",
        "user_folders",
        "projects",
        "tags",
    ]
    counts_lines: list[str] = []
    for k in count_keys:
        if not _has_key(k):
            counts_lines.append(f"{k} = true\n")
    if counts_lines:
        if "sidebar_counts" not in raw:
            missing.append("\n[sidebar_counts]\n")
        missing.extend(counts_lines)

    if not missing:
        return
    try:
        with open(path, "a", encoding="utf-8") as fh:
            fh.writelines(missing)
    except OSError:
        pass


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
        _ensure_config_defaults(cfg_path, data)
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
        startup_focus_sidebar=bool(
            ui_section.get("startup_focus_sidebar", Config.startup_focus_sidebar)
        ),
        theme=str(ui_section.get("theme", Config.theme)),
        border_style=str(ui_section.get("border_style", Config.border_style)),
        border_block_size=int(
            ui_section.get("border_block_size", Config.border_block_size)
        ),
        border_text=str(ui_section.get("border_text", Config.border_text)),
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
default_view = "today"

# Color palette: "blue" | "red" | "yellow" | "green"
theme = "blue"

# Screen border: "none" | "yellow_grey" | "red_grey"
border_style = "none"

# Number of cells per color block in the border (when border_style != "none").
border_block_size = 3

# Optional text label rendered inside the screen border.
border_text = ""

[sidebar_counts]
# Set any entry to false to hide counts for that section.
inbox = true
today = true
upcoming = true
waiting_on = true
someday = true
reference = true
logbook = true
user_folders = true
projects = true
tags = true
"""
    path.write_text(content)
