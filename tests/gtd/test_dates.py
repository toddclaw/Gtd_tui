import pytest
from datetime import date

from gtd_tui.gtd.dates import InvalidDateError, parse_date_input

TODAY = date(2026, 3, 13)


def test_empty_string_returns_none():
    assert parse_date_input("", today=TODAY) is None


def test_whitespace_only_returns_none():
    assert parse_date_input("   ", today=TODAY) is None


def test_absolute_iso_date():
    assert parse_date_input("2026-03-20", today=TODAY) == date(2026, 3, 20)


def test_relative_days():
    assert parse_date_input("+3d", today=TODAY) == date(2026, 3, 16)


def test_relative_weeks():
    assert parse_date_input("+2w", today=TODAY) == date(2026, 3, 27)


def test_relative_months():
    assert parse_date_input("+1m", today=TODAY) == date(2026, 4, 13)


def test_relative_years():
    assert parse_date_input("+1y", today=TODAY) == date(2027, 3, 13)


def test_relative_zero_days():
    assert parse_date_input("+0d", today=TODAY) == TODAY


def test_multi_digit_relative():
    assert parse_date_input("+14d", today=TODAY) == date(2026, 3, 27)


def test_invalid_string_raises():
    with pytest.raises(InvalidDateError):
        parse_date_input("next tuesday", today=TODAY)


def test_invalid_format_raises():
    with pytest.raises(InvalidDateError):
        parse_date_input("13-03-2026", today=TODAY)  # wrong order


def test_invalid_unit_raises():
    with pytest.raises(InvalidDateError):
        parse_date_input("+1x", today=TODAY)


def test_month_overflow_clamps_to_last_day():
    # Jan 31 + 1 month → Feb 28 (not Feb 31)
    jan31 = date(2026, 1, 31)
    assert parse_date_input("+1m", today=jan31) == date(2026, 2, 28)


def test_month_overflow_on_leap_year():
    # Jan 31 + 1 month in leap year → Feb 29
    jan31 = date(2024, 1, 31)
    assert parse_date_input("+1m", today=jan31) == date(2024, 2, 29)


def test_year_overflow_on_leap_day():
    # Feb 29 2024 + 1 year → Feb 28 2025 (2025 is not a leap year)
    leap_day = date(2024, 2, 29)
    assert parse_date_input("+1y", today=leap_day) == date(2025, 2, 28)


def test_year_to_another_leap_year():
    # Feb 29 2024 + 4 years → Feb 29 2028 (2028 is a leap year)
    leap_day = date(2024, 2, 29)
    assert parse_date_input("+4y", today=leap_day) == date(2028, 2, 29)
