import pytest

from datetime import date, datetime, timedelta

from Library.Utility.Datetime import datetime_to_epoch, epoch_to_datetime, is_summer_time, is_winter_time, parse_datetime

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
    unit = timedelta(microseconds=1)
    dt = datetime(2023, 6, 15, 9, 30, 0, 123456)
    assert epoch_to_datetime(datetime_to_epoch(dt, unit=unit), unit=unit) == dt

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
