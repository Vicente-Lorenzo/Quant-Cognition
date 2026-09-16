from Library.Formulas import formula
from Library.Utility import datetime_to_string, local_now

def _now_(fmt: str) -> str:
    return datetime_to_string(local_now(), fmt)

@formula
def datetime_now():
    return _now_("%Y-%m-%d %H:%M:%S")

@formula
def datetime_ms_now():
    return _now_("%Y-%m-%d %H:%M:%S.%f")[:-3]

@formula
def date_now():
    return _now_("%Y-%m-%d")

@formula
def time_now():
    return _now_("%H:%M:%S")

@formula
def year_now():
    return _now_("%Y")

@formula
def month_now():
    return _now_("%m")

@formula
def day_now():
    return _now_("%d")

@formula
def hour_now():
    return _now_("%H")

@formula
def minute_now():
    return _now_("%M")

@formula
def second_now():
    return _now_("%S")

@formula
def millisecond_now():
    return int(_now_("%f")) // 1000