"""Tests for scripts/reorder_changelog_section.py."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "reorder_changelog_section",
    _REPO / "scripts" / "reorder_changelog_section.py",
)
assert _SPEC and _SPEC.loader
_mod = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_mod)


def test_parse_version_block() -> None:
    text = """## [0.0.1] — 2020-01-01

### Fixed
- a

---

## [0.0.2]
### Added
- z
"""
    lines = _mod._parse_version_block(text, "0.0.1")
    assert lines is not None
    joined = "".join(lines)
    assert "### Fixed" in joined
    assert "0.0.2" not in joined


def test_reorder_sections_fixed_last() -> None:
    section = [
        "### Fixed\n",
        "- bug\n",
        "### Added\n",
        "- feat\n",
    ]
    out = _mod.reorder_changelog_section_lines(section)
    assert out.index("### Added") < out.index("### Fixed")


def test_sort_added_major_first() -> None:
    section = [
        "### Added\n",
        "- small thing\n",
        "- **BACKLOG-99** big\n",
    ]
    out = _mod.reorder_changelog_section_lines(section)
    assert out.index("BACKLOG") < out.index("small thing")
