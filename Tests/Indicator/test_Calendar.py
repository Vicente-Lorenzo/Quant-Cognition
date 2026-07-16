import pytest
from datetime import datetime
from Library.Database.Dataframe import pl
from Library.Indicator.Fundamental.Calendar import CalendarAPI

def test_url():
    assert CalendarAPI._url_(datetime(2026, 7, 6)) == "https://www.forexfactory.com/calendar?week=jul6.2026"

@pytest.mark.parametrize("text, expected", [
    (None, None),
    ("", None),
    ("Pass", None),
    ("0.3%", 0.3),
    ("-0.4%", -0.4),
    ("2.50%", 2.5),
    ("<0.1%", 0.1),
    ("38.4", 38.4),
    ("-3.1", -3.1),
    ("1,234.5", 1234.5),
    ("215K", 215e3),
    ("18.2K", 18.2e3),
    ("3.0M", 3e6),
    ("-77.6B", -77.6e9),
    ("3.06T", 3.06e12),
    ("3.09|1.0", 3.09)
])
def test_value(text, expected):
    assert CalendarAPI._value_(text) == expected

def test_extract():
    html = 'calendarComponentStates[1] = { days: [{"events":[{"id":1,"name":"CPI \\"core\\" [y/y]"}]}], other: [] };'
    days = CalendarAPI._extract_(html)
    assert days == [{"events": [{"id": 1, "name": 'CPI "core" [y/y]'}]}]
    assert CalendarAPI._extract_("<html></html>") == []

def test_rows():
    days = [{"events": [{
        "id": 148100, "ebaseId": 293, "dateline": 1735689600, "currency": "AUD", "country": "AU",
        "name": "MI Inflation Expectations", "impactClass": "icon--ff-impact-red",
        "actual": "4.7%", "forecast": "4.9%", "previous": "5.5%", "revision": "5.6%",
        "actualBetterWorse": 2, "revisionBetterWorse": 1
    }, {
        "id": 148101, "ebaseId": 10, "dateline": None, "currency": "", "country": "",
        "name": "", "impactClass": "icon--ff-impact-gra",
        "actual": "", "forecast": "", "previous": "", "revision": "",
        "actualBetterWorse": 0, "revisionBetterWorse": 0
    }]}]
    rows = CalendarAPI._rows_(days)
    assert len(rows) == 2
    assert rows[0]["UID"] == 148100
    assert rows[0]["Event"] == 293
    assert rows[0]["Timestamp"] == datetime(2025, 1, 1)
    assert rows[0]["Currency"] == "AUD"
    assert rows[0]["Country"] == "AU"
    assert rows[0]["Title"] == "MI Inflation Expectations"
    assert rows[0]["Impact"] == "High"
    assert rows[0]["Actual"] == "4.7%"
    assert rows[0]["ActualValue"] == 4.7
    assert rows[0]["ForecastValue"] == 4.9
    assert rows[0]["PreviousValue"] == 5.5
    assert rows[0]["RevisionValue"] == 5.6
    assert rows[0]["ActualBetter"] == -1
    assert rows[0]["RevisionBetter"] == 1
    assert rows[1]["Event"] == 10
    assert rows[1]["Timestamp"] is None
    assert rows[1]["Currency"] is None
    assert rows[1]["Impact"] == "Holiday"
    assert rows[1]["Actual"] is None
    assert rows[1]["ActualValue"] is None
    assert rows[1]["ActualBetter"] is None
    assert rows[1]["RevisionBetter"] is None

def test_frame():
    frame = CalendarAPI._frame_(CalendarAPI._rows_([{"events": [{
        "id": 1, "ebaseId": 2, "dateline": 1784163600, "currency": "USD", "country": "US",
        "name": "CPI y/y", "impactClass": "icon--ff-impact-red",
        "actual": "2.1%", "forecast": "2.0%", "previous": "1.9%", "revision": "",
        "actualBetterWorse": 1, "revisionBetterWorse": 0
    }]}]))
    assert frame.height == 1
    assert frame["UID"].dtype == CalendarAPI._frame_([]).schema["UID"]
    assert frame["ActualValue"].dtype.is_float()
    assert frame["ActualBetter"][0] == 1
    assert frame["RevisionBetter"][0] is None

def test_push_idempotent():
    from Library.Database.Postgres.Postgres import PostgresDatabaseAPI
    frame = CalendarAPI._frame_(CalendarAPI._rows_([{"events": [{
        "id": -1, "ebaseId": -1, "dateline": 1735689600, "currency": "USD", "country": "US",
        "name": "Idempotency Probe", "impactClass": "icon--ff-impact-yel",
        "actual": "1.0%", "forecast": "1.0%", "previous": "1.0%", "revision": "",
        "actualBetterWorse": 0, "revisionBetterWorse": 0
    }]}])).with_columns(pl.lit("Test").alias("UpdatedBy"), pl.lit(datetime.now()).alias("UpdatedAt"))
    with PostgresDatabaseAPI(database="Tests") as db:
        CalendarAPI(db=db, migrate=True, autosave=False, autoload=False)
        try:
            CalendarAPI.push(db, frame)
            CalendarAPI.push(db, frame)
            probe = CalendarAPI.pull(db).filter(pl.col("UID") == -1)
            assert probe.height == 1
            assert probe["Title"][0] == "Idempotency Probe"
            assert probe["ActualValue"][0] == 1.0
        finally:
            db.remove(schema=CalendarAPI.Schema, table=CalendarAPI.Table, condition='"UID" < 0')