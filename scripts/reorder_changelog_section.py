#!/usr/bin/env python3
"""Extract a version section from CHANGELOG.md and reorder for GitHub releases.

Output order:
- ### Added — bullets sorted with "major" items first (BACKLOG refs, then other bold
  lead-ins), then shorter / less prominent bullets
- ### Changed
- ### Fixed
- Any other ### sections (Deprecated, Removed, Security, etc.) in Keep a Changelog order

Usage:
    python scripts/reorder_changelog_section.py <version> [CHANGELOG.md]

Prints the section body (no leading ## [version] line) to stdout.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Subsections after Added/Changed/Fixed in Keep a Changelog order
_TAIL_ORDER = ("Deprecated", "Removed", "Security")

_SECTION_HEADER = re.compile(r"^###\s+(\S+)\s*$")


def _major_rank(line: str) -> tuple[int, int]:
    """Lower tuple sorts first = more prominent for Added section."""
    stripped = line.strip()
    if not stripped.startswith("-"):
        return (2, len(stripped))
    # BACKLOG / issue references → treat as major feature callouts
    if re.search(r"\bBACKLOG-\d+", stripped):
        return (0, len(stripped))
    # Bold lead-in like - **Feature**:
    if re.match(r"^-\s+\*\*", stripped):
        return (1, -len(stripped))
    return (2, len(stripped))


def _parse_version_block(text: str, version: str) -> list[str] | None:
    """Return lines inside ## [version] ... until --- or next ## [."""
    lines = text.splitlines(keepends=True)
    prefix = f"## [{version}]"
    start = None
    for i, line in enumerate(lines):
        if not line.startswith(prefix):
            continue
        rest = line[len(prefix) :].strip()
        if rest == "" or rest.startswith("—") or rest.startswith("-"):
            start = i + 1
            break
    if start is None:
        return None

    out: list[str] = []
    for line in lines[start:]:
        if line.strip() == "---":
            break
        if line.startswith("## ["):
            break
        out.append(line)
    return out


def _split_into_subsections(
    section_lines: list[str],
) -> tuple[list[str], dict[str, list[str]]]:
    """Leading lines before first ###, then mapping section title -> full lines including ### header."""
    preamble: list[str] = []
    by_name: dict[str, list[str]] = {}
    current: str | None = None
    buf: list[str] = []

    for line in section_lines:
        m = _SECTION_HEADER.match(line.rstrip("\n"))
        if m:
            if current is not None:
                by_name[current] = buf
            current = m.group(1)
            buf = [line]
        else:
            if current is None:
                preamble.append(line)
            else:
                buf.append(line)
    if current is not None:
        by_name[current] = buf
    return preamble, by_name


def _sort_added_section(lines: list[str]) -> list[str]:
    """Sort bullet groups under ### Added (header line first)."""
    if not lines:
        return lines
    header = lines[0]
    body = lines[1:]
    groups: list[list[str]] = []
    current: list[str] = []
    for line in body:
        if line.strip().startswith("-"):
            if current:
                groups.append(current)
            current = [line]
        else:
            if current:
                current.append(line)
            else:
                groups.append([line])
    if current:
        groups.append(current)
    groups.sort(key=lambda g: _major_rank(g[0]))
    return [header, *[ln for g in groups for ln in g]]


def reorder_changelog_section_lines(section_lines: list[str]) -> str:
    """Reorder ### subsections and sort ### Added bullets."""
    if not section_lines:
        return ""

    preamble, by_name = _split_into_subsections(section_lines)
    out_parts: list[str] = []
    out_parts.extend(preamble)

    for sec in ("Added", "Changed", "Fixed"):
        if sec in by_name:
            block = by_name.pop(sec)
            if sec == "Added":
                block = _sort_added_section(block)
            out_parts.extend(block)

    for sec in _TAIL_ORDER:
        if sec in by_name:
            out_parts.extend(by_name.pop(sec))

    for name in sorted(by_name.keys()):
        out_parts.extend(by_name[name])

    text = "".join(out_parts).rstrip()
    return text + "\n" if text else ""


def main() -> int:
    if len(sys.argv) < 2:
        print(
            "Usage: reorder_changelog_section.py <version> [CHANGELOG.md]",
            file=sys.stderr,
        )
        return 2
    version = sys.argv[1]
    path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("CHANGELOG.md")
    text = path.read_text(encoding="utf-8")
    block = _parse_version_block(text, version)
    if block is None:
        print(f"No section ## [{version}] in {path}", file=sys.stderr)
        return 1
    sys.stdout.write(reorder_changelog_section_lines(block))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
