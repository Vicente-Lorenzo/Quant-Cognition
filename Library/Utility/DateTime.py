from datetime import datetime, date, time
from dateutil.relativedelta import relativedelta, weekday

from Library.Database.Enumeration import Enumeration

class Weekday(Enumeration):
    Monday = 0
    Tuesday = 1
    Wednesday = 2
    Thursday = 3
    Friday = 4
    Saturday = 5
    Sunday = 6

def datetime_to_string(dt: datetime | date | time, fmt: str) -> str:
    return dt.strftime(fmt)

def string_to_datetime(date_str: str, fmt_str: str) -> datetime:
    return datetime.strptime(date_str, fmt_str)

def datetime_to_timestamp(dt: datetime | date | time, milliseconds: bool = False) -> float:
    ts = dt.timestamp()
    return ts * 1000 if milliseconds else ts

def timestamp_to_datetime(ts: float, milliseconds: bool = False) -> datetime:
    return datetime.fromtimestamp(ts / 1000 if milliseconds else ts)

def datetime_to_iso(dt: datetime) -> str:
    return dt.isoformat()

def iso_to_datetime(iso_str: str) -> datetime:
    return datetime.fromisoformat(iso_str)

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