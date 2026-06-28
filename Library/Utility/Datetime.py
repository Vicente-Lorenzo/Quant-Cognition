from typing import Final, Union
from datetime import datetime, date, time, timedelta
from dateutil.relativedelta import relativedelta, weekday

from Library.Utility.Enumeration import EnumerationAPI

EPOCH: Final[datetime] = datetime(1970, 1, 1)
MILLISECOND: Final[timedelta] = timedelta(milliseconds=1)
MICROSECOND: Final[timedelta] = timedelta(microseconds=1)

class Weekday(EnumerationAPI):
    Monday = 0
    Tuesday = 1
    Wednesday = 2
    Thursday = 3
    Friday = 4
    Saturday = 5
    Sunday = 6

def datetime_to_string(dt: Union[datetime, date, time], fmt: str) -> str:
    return dt.strftime(fmt)

def string_to_datetime(date_str: str, fmt_str: str) -> datetime:
    return datetime.strptime(date_str, fmt_str)

def datetime_to_timestamp(dt: Union[datetime, date, time], milliseconds: bool = False) -> float:
    ts = dt.timestamp()
    return ts * 1000 if milliseconds else ts

def datetime_to_epoch(dt: datetime, epoch: datetime = EPOCH, unit: timedelta = MILLISECOND) -> int:
    return (dt - epoch) // unit

def epoch_to_datetime(value: int, epoch: datetime = EPOCH, unit: timedelta = MILLISECOND) -> datetime:
    return epoch + value * unit

def timestamp_to_datetime(ts: float, milliseconds: bool = False) -> datetime:
    return datetime.fromtimestamp(ts / 1000 if milliseconds else ts)

def datetime_to_iso(dt: datetime) -> str:
    return dt.isoformat()

def iso_to_datetime(iso_str: str) -> datetime:
    return datetime.fromisoformat(iso_str)

def parse_datetime(value: Union[str, date, datetime], end_of_day: bool = False) -> datetime:
    if isinstance(value, datetime): return value
    if isinstance(value, date): base = datetime(value.year, value.month, value.day)
    else:
        base = None
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d", "%d/%m/%Y"):
            try: base = datetime.strptime(value, fmt); break
            except ValueError: continue
        if base is None: base = datetime.fromisoformat(value)
    return base.replace(hour=23, minute=59, second=59, microsecond=999999) if end_of_day else base

def seconds_to_string(seconds: float) -> str:
    seconds, milliseconds = divmod(seconds, 1)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    months, days = divmod(days, 12)
    years, months = divmod(months, 12)
    result = []
    if years:
        result.append(f"{round(years)} years")
    if months:
        result.append(f"{round(months)} months")
    if days:
        result.append(f"{round(days)} days")
    if hours:
        result.append(f"{round(hours)} hours")
    if minutes:
        result.append(f"{round(minutes)} minutes")
    if seconds:
        result.append(f"{round(seconds)} seconds")
    if milliseconds:
        result.append(f"{round(milliseconds * 1000)} milliseconds")
    return " ".join(result)

def weekday_shift_datetime(wd: Weekday, shift: int, today: datetime = datetime.today()) -> datetime:
    shift = shift - 1 if today.weekday() > wd.value else shift
    return today + relativedelta(weekday=weekday(wd.value)(shift))

def monday_shift_datetime(shift: int, today: datetime = datetime.today()) -> datetime:
    return weekday_shift_datetime(wd=Weekday.Monday, shift=shift, today=today)

def tuesday_shift_datetime(shift: int, today: datetime = datetime.today()) -> datetime:
    return weekday_shift_datetime(wd=Weekday.Tuesday, shift=shift, today=today)

def wednesday_shift_datetime(shift: int, today: datetime = datetime.today()) -> datetime:
    return weekday_shift_datetime(wd=Weekday.Wednesday, shift=shift, today=today)

def thursday_shift_datetime(shift: int, today: datetime = datetime.today()) -> datetime:
    return weekday_shift_datetime(wd=Weekday.Thursday, shift=shift, today=today)

def friday_shift_datetime(shift: int, today: datetime = datetime.today()) -> datetime:
    return weekday_shift_datetime(wd=Weekday.Friday, shift=shift, today=today)

def saturday_shift_datetime(shift: int, today: datetime = datetime.today()) -> datetime:
    return weekday_shift_datetime(wd=Weekday.Saturday, shift=shift, today=today)

def sunday_shift_datetime(shift: int, today: datetime = datetime.today()) -> datetime:
    return weekday_shift_datetime(wd=Weekday.Sunday, shift=shift, today=today)

def _last_weekday_(year: int, month: int, weekday: int) -> datetime:
    last = datetime(year, 12, 31) if month == 12 else datetime(year, month + 1, 1) - timedelta(days=1)
    return last - timedelta(days=(last.weekday() - weekday) % 7)

def _nth_weekday_(year: int, month: int, weekday: int, n: int) -> datetime:
    first = datetime(year, month, 1)
    return first + timedelta(days=(weekday - first.weekday()) % 7 + (n - 1) * 7)

def is_summer_time(timestamp: datetime, region: str = "EU") -> bool:
    year = timestamp.year
    if region == "EU":
        spring = _last_weekday_(year, 3, Weekday.Sunday.value).replace(hour=1)
        autumn = _last_weekday_(year, 10, Weekday.Sunday.value).replace(hour=1)
    elif region == "US":
        spring = _nth_weekday_(year, 3, Weekday.Sunday.value, 2).replace(hour=2)
        autumn = _nth_weekday_(year, 11, Weekday.Sunday.value, 1).replace(hour=2)
    else:
        raise ValueError(f"Region {region}: Failed · Due to unsupported daylight-saving region")
    return spring <= timestamp < autumn

def is_winter_time(timestamp: datetime, region: str = "EU") -> bool:
    return not is_summer_time(timestamp, region)