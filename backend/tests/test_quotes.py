"""Tests for quote services (en + nl) — pure functions, no mocking."""

from datetime import date, timedelta

import pytest

from src.services.quotes import en, nl
from src.services.quotes._utils import easter

# ── Easter algorithm ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("year,expected", [
    (2024, date(2024, 3, 31)),
    (2025, date(2025, 4, 20)),
    (2026, date(2026, 4, 5)),
])
def test_easter_known_dates(year, expected):
    assert easter(year) == expected


# ── English holiday quotes ─────────────────────────────────────────────────────

@pytest.mark.parametrize("d,expected_fragment", [
    (date(2026, 1, 1),  "blank page"),
    (date(2026, 2, 14), "small things"),
    (date(2026, 3, 8),  "women"),
    (date(2026, 3, 17), "luck"),
    (date(2026, 4, 1),  "as it seems"),
    (date(2026, 5, 1),  "Rest"),
    (date(2026, 10, 31), "dark"),
    (date(2026, 12, 24), "anticipation"),
    (date(2026, 12, 25), "best gift"),
    (date(2026, 12, 26), "Two days"),
    (date(2026, 12, 31), "lap around"),
])
def test_en_holiday_fixed(d, expected_fragment):
    result = en.holiday_quote(d)
    assert result is not None
    assert expected_fragment.lower() in result.lower()


def test_en_holiday_easter_and_relatives():
    e = easter(2026)
    assert en.holiday_quote(e - timedelta(days=2)) is not None  # Good Friday
    assert en.holiday_quote(e) is not None                      # Easter Sunday
    assert en.holiday_quote(e + timedelta(days=1)) is not None  # Easter Monday
    assert en.holiday_quote(e + timedelta(days=39)) is not None # Ascension
    assert en.holiday_quote(e + timedelta(days=49)) is not None # Pentecost
    assert en.holiday_quote(e + timedelta(days=50)) is not None # Whit Monday


def test_en_holiday_miss():
    # Ordinary Tuesday in June — no holiday
    assert en.holiday_quote(date(2026, 6, 16)) is None


# ── English weather quotes ─────────────────────────────────────────────────────

@pytest.mark.parametrize("condition,temp,expect_result", [
    ("sunny",            30.0, True),   # hot sunny
    ("sunny",            22.0, True),   # warm sunny
    ("partlycloudy",     20.0, True),   # warm partly cloudy
    ("rainy",            15.0, True),
    ("pouring",          10.0, True),
    ("lightning-rainy",  10.0, True),
    ("snowy",            -2.0, True),
    ("snowy-rainy",       0.0, True),
    ("lightning",        20.0, True),
    ("fog",              10.0, True),
    ("windy",            15.0, True),
    ("windy-variant",    15.0, True),
    (None,               20.0, False),  # None condition → None
    ("unknown-cond",     20.0, False),  # unrecognised → None
    ("sunny",            10.0, False),  # sunny but cold → no quote
    ("partlycloudy",     10.0, False),  # partly cloudy + cold → no quote
])
def test_en_weather_quote(condition, temp, expect_result):
    result = en.weather_quote(condition, temp, date(2026, 3, 15))
    assert (result is not None) == expect_result


def test_en_weather_quote_returns_string():
    result = en.weather_quote("rainy", 10.0, date(2026, 3, 15))
    assert isinstance(result, str) and len(result) > 0


# ── English weekday quotes ─────────────────────────────────────────────────────

@pytest.mark.parametrize("d", [
    date(2026, 3, 16),  # Monday
    date(2026, 3, 17),  # Tuesday
    date(2026, 3, 18),  # Wednesday
    date(2026, 3, 19),  # Thursday
    date(2026, 3, 20),  # Friday
    date(2026, 3, 21),  # Saturday
    date(2026, 3, 22),  # Sunday
])
def test_en_weekday_quote(d):
    result = en.weekday_quote(d)
    assert isinstance(result, str) and len(result) > 0


def test_en_weekday_quote_deterministic():
    d = date(2026, 3, 16)
    assert en.weekday_quote(d) == en.weekday_quote(d)


# ── Dutch holiday quotes ───────────────────────────────────────────────────────

@pytest.mark.parametrize("d,expected_fragment", [
    (date(2026, 1, 1),  "nieuw jaar"),
    (date(2026, 2, 14), "kleine dingen"),
    (date(2026, 3, 8),  "vrouwen"),
    (date(2026, 4, 27), "Oranje"),      # Koningsdag — NL only
    (date(2026, 5, 1),  "Rust"),
    (date(2026, 5, 5),  "Vrijheid"),
    (date(2026, 10, 31), "charme"),
    (date(2026, 11, 11), "Sint Maarten"),
    (date(2026, 12, 5),  "gedicht"),
    (date(2026, 12, 24), "magie"),
    (date(2026, 12, 25), "mooiste cadeau"),
    (date(2026, 12, 26), "twee dagen"),
    (date(2026, 12, 31), "rondje"),
])
def test_nl_holiday_fixed(d, expected_fragment):
    result = nl.holiday_quote(d)
    assert result is not None
    assert expected_fragment.lower() in result.lower()


def test_nl_holiday_easter_and_relatives():
    e = easter(2026)
    assert nl.holiday_quote(e - timedelta(days=2)) is not None
    assert nl.holiday_quote(e) is not None
    assert nl.holiday_quote(e + timedelta(days=1)) is not None
    assert nl.holiday_quote(e + timedelta(days=39)) is not None
    assert nl.holiday_quote(e + timedelta(days=49)) is not None
    assert nl.holiday_quote(e + timedelta(days=50)) is not None


def test_nl_holiday_miss():
    assert nl.holiday_quote(date(2026, 6, 16)) is None


# ── Dutch weather quotes ───────────────────────────────────────────────────────

@pytest.mark.parametrize("condition,temp,expect_result", [
    ("sunny",           30.0, True),
    ("sunny",           22.0, True),
    ("partlycloudy",    20.0, True),
    ("rainy",           15.0, True),
    ("pouring",         10.0, True),
    ("lightning-rainy", 10.0, True),
    ("snowy",           -2.0, True),
    ("snowy-rainy",      0.0, True),
    ("lightning",       20.0, True),
    ("fog",             10.0, True),
    ("windy",           15.0, True),
    ("windy-variant",   15.0, True),
    (None,              20.0, False),
    ("unknown-cond",    20.0, False),
    ("sunny",           10.0, False),
    ("partlycloudy",    10.0, False),
])
def test_nl_weather_quote(condition, temp, expect_result):
    result = nl.weather_quote(condition, temp, date(2026, 3, 15))
    assert (result is not None) == expect_result


# ── Dutch weekday quotes ───────────────────────────────────────────────────────

@pytest.mark.parametrize("d", [
    date(2026, 3, 16),  # Maandag
    date(2026, 3, 17),  # Dinsdag
    date(2026, 3, 18),  # Woensdag
    date(2026, 3, 19),  # Donderdag
    date(2026, 3, 20),  # Vrijdag
    date(2026, 3, 21),  # Zaterdag
    date(2026, 3, 22),  # Zondag
])
def test_nl_weekday_quote(d):
    result = nl.weekday_quote(d)
    assert isinstance(result, str) and len(result) > 0
