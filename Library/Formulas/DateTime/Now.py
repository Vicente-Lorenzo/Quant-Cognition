from datetime import datetime

from Library.Formulas import formula
from Library.Utility import datetime_to_string

@formula
def datetime_now():
    return datetime_to_string(datetime.now(), "%Y-%m-%d %H:%M:%S")

@formula
def datetime_ms_now():
    return datetime_to_string(datetime.now(), "%Y-%m-%d %H:%M:%S.f")[:-3]

@formula
def date_now():
    return datetime_to_string(datetime.now(), "%Y-%m-%d")

@formula
def time_now():
    return datetime_to_string(datetime.now(), "%H:%M:%S")

@formula
def year_now():
    return datetime_to_string(datetime.now(), "%Y")

@formula
def month_now():
    return datetime_to_string(datetime.now(), "%m")

@formula
def day_now():
    return datetime_to_string(datetime.now(), "%d")

@formula
def hour_now():
    return datetime_to_string(datetime.now(), "%H")

@formula
def minute_now():
    return datetime_to_string(datetime.now(), "%M")

@formula
def second_now():
    return datetime_to_string(datetime.now(), "%S")

@formula
def millisecond_now():
    return datetime.now().microsecond // 1000