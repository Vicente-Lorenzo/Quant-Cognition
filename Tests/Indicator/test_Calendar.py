import pytest
from datetime import datetime, timedelta, timezone
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
        CalendarAPI(db=db, migrate=True, autoload=False)
        try:
            CalendarAPI.push(db, frame)
            CalendarAPI.push(db, frame)
            probe = CalendarAPI.pull(db).filter(pl.col("UID") == -1)
            assert probe.height == 1
            assert probe["Title"][0] == "Idempotency Probe"
            assert probe["ActualValue"][0] == 1.0
        finally:
            db.remove(schema=CalendarAPI.Schema, table=CalendarAPI.Table, condition='"UID" < 0')
def probe(actual: str, dateline: int = 1925472600) -> list:
    return CalendarAPI._rows_([{"events": [{"id": -11, "ebaseId": -11, "dateline": dateline, "currency": "USD", "country": "US", "name": "History Probe", "impactClass": "icon--ff-impact-red",
                                            "actual": actual, "forecast": "1.0%", "previous": "0.9%", "revision": "", "actualBetterWorse": 0, "revisionBetterWorse": 0}]}])

@pytest.fixture
def calendar():
    from Library.Database.Postgres.Postgres import PostgresDatabaseAPI
    from Library.Indicator.Fundamental.Calendar import CalendarHistoryAPI
    with PostgresDatabaseAPI(database="Tests") as db:
        CalendarAPI(db=db, migrate=True, autoload=False)
        CalendarHistoryAPI(db=db, migrate=True, autoload=False)
        db.remove(schema=CalendarAPI.Schema, table=CalendarAPI.Table, condition='"UID" < 0')
        try: yield db
        finally: db.remove(schema=CalendarAPI.Schema, table=CalendarAPI.Table, condition='"UID" < 0')

def test_a_release_is_stored_once_and_each_change_of_its_values_is_dated(calendar):
    from Library.Indicator.Fundamental.Calendar import CalendarHistoryAPI
    assert CalendarAPI.store(calendar, probe(""), "Tester") == (1, 1)
    assert CalendarAPI.store(calendar, probe(""), "Tester") == (1, 0)
    assert CalendarAPI.store(calendar, probe("1.2%"), "Tester") == (1, 1)
    history = calendar.records(schema=CalendarHistoryAPI.Schema, table=CalendarHistoryAPI.Table, condition='"Calendar" = -11', order='"Timestamp"')
    assert [row["Actual"] for row in history] == [None, "1.2%"]
    assert CalendarAPI.pull(calendar).filter(pl.col("UID") == -11)["Actual"][0] == "1.2%"

def test_a_week_awaiting_its_actuals_is_incomplete_until_they_arrive(calendar):
    week, since, until = datetime(2031, 1, 6), datetime(2031, 1, 1), datetime(2031, 1, 31)
    CalendarAPI.store(calendar, probe(""), "Tester")
    assert week in CalendarAPI.weeks(calendar) and CalendarAPI.incomplete(calendar, since, until) == {week}
    CalendarAPI.store(calendar, probe("1.2%"), "Tester")
    assert CalendarAPI.incomplete(calendar, since, until) == set()

def test_the_service_asks_for_missing_and_incomplete_weeks_but_never_the_current_one(calendar):
    from Library.Data.Calendar import CalendarServiceAPI
    service = CalendarServiceAPI(horizon=datetime(2031, 1, 6), database="Tests", vault="Tests")
    CalendarAPI.store(calendar, probe(""), "Tester")
    now = datetime(2031, 1, 22, 12)
    assert service._missing_(calendar, now) == [datetime(2031, 1, 6), datetime(2031, 1, 13)]
    CalendarAPI.store(calendar, probe("1.2%"), "Tester")
    assert service._missing_(calendar, now) == [datetime(2031, 1, 13)]

def test_a_week_runs_monday_to_sunday_across_the_two_pages_it_spans(monkeypatch):
    requested = []
    stamps = [datetime(2031, 1, 5, 21), datetime(2031, 1, 6, 1), datetime(2031, 1, 12, 23, 50), datetime(2031, 1, 13, 1)]
    def page(cls, day):
        requested.append(day)
        return [{"UID": index, "Timestamp": stamp} for index, stamp in enumerate(stamps) if day - timedelta(days=(day.weekday() + 1) % 7) <= stamp < day - timedelta(days=(day.weekday() + 1) % 7) + timedelta(days=7)]
    monkeypatch.setattr(CalendarAPI, "_page_", classmethod(page))
    assert [row["Timestamp"] for row in CalendarAPI.week(datetime(2031, 1, 9, 15))] == [datetime(2031, 1, 6, 1), datetime(2031, 1, 12, 23, 50)]
    assert requested == [datetime(2031, 1, 6), datetime(2031, 1, 12)]

def test_a_sunday_evening_release_is_awaited_in_its_monday_week(calendar):
    from Library.Data.Calendar import CalendarServiceAPI
    service = CalendarServiceAPI(horizon=datetime(2031, 1, 6), database="Tests", vault="Tests")
    release = datetime(2031, 1, 12, 23, 50)
    CalendarAPI.store(calendar, probe("", int(release.replace(tzinfo=timezone.utc).timestamp())), "Tester")
    assert service._pending_(calendar, datetime(2031, 1, 12, 23, 55)) == {datetime(2031, 1, 6)}

def test_a_page_without_calendar_data_fails_loudly(monkeypatch):
    monkeypatch.setattr(CalendarAPI, "_request_", classmethod(lambda cls, url, retries=3, backoff=3.0: "<html>Just a moment</html>"))
    with pytest.raises(ValueError, match="carries no calendar data"): CalendarAPI.week(datetime(2031, 1, 6))

@pytest.mark.parametrize("local, zone, utc", [
    (datetime(2026, 1, 13, 8, 30), "America/New_York", datetime(2026, 1, 13, 13, 30)),
    (datetime(2026, 3, 10, 8, 30), "America/New_York", datetime(2026, 3, 10, 12, 30)),
    (datetime(2026, 7, 14, 8, 30), "America/New_York", datetime(2026, 7, 14, 12, 30)),
    (datetime(2026, 9, 18, 12, 0), "Europe/London", datetime(2026, 9, 18, 11, 0)),
    (datetime(2026, 11, 5, 12, 0), "Europe/London", datetime(2026, 11, 5, 12, 0)),
])
def test_a_release_is_stored_at_its_utc_instant_in_either_daylight_saving_regime(local, zone, utc):
    from zoneinfo import ZoneInfo
    dateline = int(local.replace(tzinfo=ZoneInfo(zone)).timestamp())
    row = CalendarAPI._rows_([{"events": [{"id": 1, "dateline": dateline, "name": "Release"}]}])[0]
    assert row["Timestamp"] == utc and row["Timestamp"].tzinfo is None