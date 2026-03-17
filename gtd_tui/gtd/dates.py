from __future__ import annotations

import re
from calendar import monthrange
from datetime import date, timedelta


class InvalidDateError(ValueError):
    """Raised when a date string cannot be parsed."""


# Weekday name → weekday() integer (Monday=0 … Sunday=6)
_WEEKDAY_NAMES: dict[str, int] = {
    "monday": 0,
    "mon": 0,
    "tuesday": 1,
    "tue": 1,
    "wednesday": 2,
    "wed": 2,
    "thursday": 3,
    "thu": 3,
    "friday": 4,
    "fri": 4,
    "saturday": 5,
    "sat": 5,
    "sunday": 6,
    "sun": 6,
}


def _next_weekday(ref: date, target_wd: int) -> date:
    """Return the next occurrence of target_wd (Mon=0) strictly after ref."""
    days_ahead = (target_wd - ref.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    return ref + timedelta(days=days_ahead)


def parse_date_input(value: str, today: date | None = None) -> date | None:
    """Parse user date input into a date object.

    Returns None if value is empty (signals "clear the date").
    Raises InvalidDateError for unrecognisable input.

    Accepted formats:
        +Nd  — N days from today
        +Nw  — N weeks from today
        +Nm  — N calendar months from today
        +Ny  — N calendar years from today
        YYYY-MM-DD — absolute ISO date
        today — today's date
        tomorrow — 1 day from today
        next week — 7 days from today
        in N day(s) / in N week(s) — relative natural language
        monday … sunday (or mon…sun) — next occurrence of that weekday
        next monday … next sunday — same as bare weekday name
    """
    ref = today or date.today()
    stripped = value.strip()

    if not stripped:
        return None

    lower = stripped.lower()

    # Natural language keywords
    if lower == "today":
        return ref

    if lower == "tomorrow":
        return ref + timedelta(days=1)

    if lower == "next week":
        return ref + timedelta(weeks=1)

    in_days = re.fullmatch(r"in (\d+) days?", lower)
    if in_days:
        return ref + timedelta(days=int(in_days.group(1)))

    in_weeks = re.fullmatch(r"in (\d+) weeks?", lower)
    if in_weeks:
        return ref + timedelta(weeks=int(in_weeks.group(1)))

    # "next <weekday>" or bare "<weekday>" / abbreviation
    next_wd = re.fullmatch(r"(?:next )?(\w+)", lower)
    if next_wd:
        wd_name = next_wd.group(1)
        if wd_name in _WEEKDAY_NAMES:
            return _next_weekday(ref, _WEEKDAY_NAMES[wd_name])

    # Compact relative: +Nd / +Nw / +Nm / +Ny
    relative = re.fullmatch(r"\+(\d+)([dwmy])", stripped)
    if relative:
        n = int(relative.group(1))
        unit = relative.group(2)
        if unit == "d":
            return ref + timedelta(days=n)
        if unit == "w":
            return ref + timedelta(weeks=n)
        if unit == "m":
            month = ref.month - 1 + n
            year = ref.year + month // 12
            month = month % 12 + 1
            day = min(ref.day, monthrange(year, month)[1])
            return date(year, month, day)
        if unit == "y":
            try:
                return date(ref.year + n, ref.month, ref.day)
            except ValueError:
                # Feb 29 in a non-leap target year → Feb 28
                return date(ref.year + n, ref.month, ref.day - 1)

    try:
        return date.fromisoformat(stripped)
    except ValueError:
        raise InvalidDateError(f"Cannot parse date: {stripped!r}")


def format_date(d: date) -> str:
    """Format a date as 'Mar 16 Mon'; appends the year if it differs from today."""
    fmt = d.strftime("%b %d %a")
    if d.year != date.today().year:
        fmt += f" {d.year}"
    return fmt
