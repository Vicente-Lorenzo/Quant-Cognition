import pytest

from datetime import date, datetime, timedelta, timezone

from Library.Utility.Datetime import EPOCH, MICROSECOND, MILLISECOND, datetime_to_epoch, epoch_to_datetime, is_summer_time, is_winter_time, local_to_utc, parse_datetime, utc_to_local, zones

def test_parse_datetime_formats():
    assert parse_datetime("2023-01-01") == datetime(2023, 1, 1)
    assert parse_datetime("01-01-2023") == datetime(2023, 1, 1)
    assert parse_datetime("2023/01/01") == datetime(2023, 1, 1)
    assert parse_datetime(date(2023, 1, 1)) == datetime(2023, 1, 1)
    assert parse_datetime(datetime(2023, 1, 1, 12)) == datetime(2023, 1, 1, 12)

def test_parse_datetime_end_of_day():
    end = parse_datetime("2023-01-01", end_of_day=True)
    assert (end.hour, end.minute, end.second, end.microsecond) == (23, 59, 59, 999999)

def test_epoch_to_datetime_inverts_datetime_to_epoch():
    assert epoch_to_datetime(0) == datetime(1970, 1, 1)
    dt = datetime(2023, 6, 15, 9, 30, 0, 123456)
    assert epoch_to_datetime(datetime_to_epoch(dt, unit=MICROSECOND), unit=MICROSECOND) == dt

def test_datetime_constants():
    assert EPOCH == datetime(1970, 1, 1)
    assert MILLISECOND == timedelta(milliseconds=1)
    assert MICROSECOND == timedelta(microseconds=1)

def test_is_summer_time_eu_boundaries():
    assert is_summer_time(datetime(2023, 1, 15)) is False
    assert is_summer_time(datetime(2023, 3, 26, 0)) is False
    assert is_summer_time(datetime(2023, 3, 26, 1)) is True
    assert is_summer_time(datetime(2023, 7, 1)) is True
    assert is_summer_time(datetime(2023, 10, 29, 0)) is True
    assert is_summer_time(datetime(2023, 10, 29, 1)) is False
    assert is_summer_time(datetime(2023, 11, 15)) is False
    assert is_summer_time(datetime(2024, 3, 31, 1)) is True
    assert is_summer_time(datetime(2024, 10, 27, 1)) is False

def test_is_summer_time_us_boundaries():
    assert is_summer_time(datetime(2023, 3, 12, 1), "US") is False
    assert is_summer_time(datetime(2023, 3, 12, 2), "US") is True
    assert is_summer_time(datetime(2023, 7, 1), "US") is True
    assert is_summer_time(datetime(2023, 11, 5, 1), "US") is True
    assert is_summer_time(datetime(2023, 11, 5, 2), "US") is False

def test_is_winter_time_is_complement():
    assert is_winter_time(datetime(2023, 1, 15)) is True
    assert is_winter_time(datetime(2023, 7, 1)) is False

def test_is_summer_time_unsupported_region():
    with pytest.raises(ValueError):
        is_summer_time(datetime(2023, 7, 1), "ZZ")

def test_zone_conversions_follow_each_zones_daylight_saving():
    assert local_to_utc(datetime(2026, 7, 1, 9), "America/New_York") == datetime(2026, 7, 1, 13)
    assert local_to_utc(datetime(2026, 1, 15, 9), "America/New_York") == datetime(2026, 1, 15, 14)
    assert utc_to_local(datetime(2026, 7, 1, 13), "America/New_York") == datetime(2026, 7, 1, 9)
    assert utc_to_local(datetime(2026, 7, 1, 23, 30), "Europe/London") == datetime(2026, 7, 2, 0, 30)

def test_an_empty_zone_means_the_system_zone():
    moment = datetime(2026, 7, 1, 4)
    assert local_to_utc(moment, "") == local_to_utc(moment, None) == local_to_utc(moment)
    assert utc_to_local(moment, "") == utc_to_local(moment)

def test_zones_are_sorted_and_carry_utc():
    names = zones()
    assert "UTC" in names and "America/New_York" in names
    assert list(names) == sorted(names)

def test_zones_offer_only_names_a_browser_accepts():
    names = zones()
    assert "Factory" not in names
    assert all(part[:1].isupper() for name in names for part in name.split("/"))

def _repeated_(zone):
    for minute in range(15, 36 * 60, 15):
        moment = datetime(2026, 10, 24, 12, tzinfo=timezone.utc) + timedelta(minutes=minute)
        before, after = (moment - timedelta(minutes=15)).astimezone(zone).utcoffset(), moment.astimezone(zone).utcoffset()
        if after < before: return moment.replace(tzinfo=None), before - after
    return None

def test_utc_to_local_marks_the_second_pass_of_a_repeated_hour():
    first, second = datetime(2026, 10, 25, 0, 30), datetime(2026, 10, 25, 1, 30)
    assert utc_to_local(first, "Europe/London") == utc_to_local(second, "Europe/London") == datetime(2026, 10, 25, 1, 30)
    assert (utc_to_local(first, "Europe/London").fold, utc_to_local(second, "Europe/London").fold) == (0, 1)
    assert local_to_utc(utc_to_local(second, "Europe/London"), "Europe/London") == second

def test_utc_to_local_marks_the_second_pass_in_the_system_zone():
    repeated = _repeated_(None)
    if repeated is None: pytest.skip("System zone repeats no hour around 2026-10-25")
    transition, width = repeated
    first, second = transition - width / 2, transition + width / 2
    assert utc_to_local(first) == utc_to_local(second)
    assert (utc_to_local(first).fold, utc_to_local(second).fold) == (0, 1)
    assert (local_to_utc(utc_to_local(first)), local_to_utc(utc_to_local(second))) == (first, second)