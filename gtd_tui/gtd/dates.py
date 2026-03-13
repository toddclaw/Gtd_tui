from __future__ import annotations

import re
from calendar import monthrange
from datetime import date, timedelta


class InvalidDateError(ValueError):
    """Raised when a date string cannot be parsed."""


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
    """
    ref = today or date.today()
    stripped = value.strip()

    if not stripped:
        return None

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
