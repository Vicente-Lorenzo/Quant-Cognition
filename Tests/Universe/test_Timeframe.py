import pytest

from Library.Universe.Timeframe import TimeframeAPI

def test_timeframe_normalize_exact_matches():
    assert TimeframeAPI.normalize("DAILY") == "D1"
    assert TimeframeAPI.normalize("D") == "D1"
    assert TimeframeAPI.normalize("DAY") == "D1"
    assert TimeframeAPI.normalize("1D") == "D1"
    assert TimeframeAPI.normalize("WEEKLY") == "W1"
    assert TimeframeAPI.normalize("W") == "W1"
    assert TimeframeAPI.normalize("WEEK") == "W1"
    assert TimeframeAPI.normalize("1W") == "W1"
    assert TimeframeAPI.normalize("MONTHLY") == "MN1"
    assert TimeframeAPI.normalize("MN") == "MN1"
    assert TimeframeAPI.normalize("MONTH") == "MN1"
    assert TimeframeAPI.normalize("1M") == "M1"
    assert TimeframeAPI.normalize("HOURLY") == "H1"
    assert TimeframeAPI.normalize("H") == "H1"
    assert TimeframeAPI.normalize("HOUR") == "H1"
    assert TimeframeAPI.normalize("1H") == "H1"
    assert TimeframeAPI.normalize("60") == "H1"
    assert TimeframeAPI.normalize("60M") == "H1"
    assert TimeframeAPI.normalize("MINUTELY") == "M1"
    assert TimeframeAPI.normalize("M") == "M1"
    assert TimeframeAPI.normalize("MINUTE") == "M1"
    assert TimeframeAPI.normalize("SECONDLY") == "S1"
    assert TimeframeAPI.normalize("S") == "S1"
    assert TimeframeAPI.normalize("SECOND") == "S1"
    assert TimeframeAPI.normalize("1S") == "S1"
    assert TimeframeAPI.normalize("YEARLY") == "Y1"
    assert TimeframeAPI.normalize("Y") == "Y1"
    assert TimeframeAPI.normalize("YEAR") == "Y1"
    assert TimeframeAPI.normalize("1Y") == "Y1"

def test_timeframe_normalize_regex():
    assert TimeframeAPI.normalize("M15") == "M15"
    assert TimeframeAPI.normalize("15M") == "M15"
    assert TimeframeAPI.normalize("H4") == "H4"
    assert TimeframeAPI.normalize("4H") == "H4"

def test_timeframe_initialization(db):
    tf = TimeframeAPI(UID="60", db=db)
    assert tf.UID == "H1"
    assert tf.Unit == "H"
    assert tf.Value == 1
    assert tf.Minutes == 60.0
    assert tf.Name == "Hour"

def test_timeframe_normalize_ticks():
    assert TimeframeAPI.normalize("TICK") == "T1"
    assert TimeframeAPI.normalize("TICKS") == "T1"
    assert TimeframeAPI.normalize("T") == "T1"
    assert TimeframeAPI.normalize("1T") == "T1"
    assert TimeframeAPI.normalize("T1") == "T1"
    assert TimeframeAPI.normalize("T50") == "T50"
    assert TimeframeAPI.normalize("50T") == "T50"

def test_timeframe_tick_inference():
    tf = TimeframeAPI(UID="T50")
    assert tf.UID == "T50"
    assert tf.Unit == "T"
    assert tf.Value == 50
    assert tf.IsTick is True
    assert tf.Minutes is None
    assert tf.Seconds is None

def test_timeframe_comparison():
    tick, tick50, m1, h1, d1 = (TimeframeAPI(UID=u) for u in ("T1", "T50", "M1", "H1", "D1"))
    assert tick < d1
    assert tick <= d1
    assert tick < tick50
    assert tick50 > tick
    assert m1 < h1
    assert h1 > m1
    assert d1 <= d1
    assert d1 >= h1
    assert d1 > h1
    assert m1 <= d1
    assert (h1 == TimeframeAPI(UID="H1")) is True
    assert (h1 == d1) is False
    assert (h1 == "H1") is False

FAMILIES = {
    "H1": ("Hour", "HOUR", "hourly", "Hourly", "H", "1H", "H1", "h1", "60", "60M", "60m"),
    "D1": ("Daily", "DAILY", "DAY", "Day", "D", "1D", "D1", "d1"),
    "M1": ("Minute", "MINUTELY", "Minutely", "M", "1M", "M1", "m1"),
    "MN1": ("Monthly", "MONTHLY", "MONTH", "Month", "MN", "1MN", "MN1", "mn1"),
    "W1": ("Weekly", "WEEKLY", "WEEK", "Week", "W", "1W", "W1", "w1"),
    "Y1": ("Yearly", "YEARLY", "YEAR", "Y", "1Y", "Y1"),
    "S1": ("Secondly", "SECOND", "S", "1S", "S1"),
    "T1": ("Tick", "TICKS", "T", "1T", "T1"),
}

@pytest.mark.parametrize("canonical, variants", sorted(FAMILIES.items()))
def test_every_spelling_of_a_timeframe_collapses_to_one_uid(canonical, variants):
    assert {TimeframeAPI.normalize(variant) for variant in variants} == {canonical}

@pytest.mark.parametrize("canonical", sorted(FAMILIES))
def test_normalize_is_idempotent(canonical):
    assert TimeframeAPI.normalize(TimeframeAPI.normalize(canonical)) == canonical

@pytest.mark.parametrize("prefixed, suffixed, canonical", [
    ("4H", "H4", "H4"), ("15M", "M15", "M15"), ("3D", "D3", "D3"),
    ("2W", "W2", "W2"), ("3MN", "MN3", "MN3"), ("12H", "H12", "H12"),
])
def test_a_multiple_reads_the_same_either_way_round(prefixed, suffixed, canonical):
    assert TimeframeAPI.normalize(prefixed) == canonical
    assert TimeframeAPI.normalize(suffixed) == canonical

def test_whitespace_and_case_never_change_the_answer():
    assert TimeframeAPI.normalize("  daily  ") == "D1"
    assert TimeframeAPI.normalize("HoUr") == "H1"

def test_distinct_timeframes_stay_distinct():
    assert len({TimeframeAPI.normalize(uid) for uid in ("H1", "H4", "M1", "M15", "D1", "D3", "W1", "MN1")}) == 8

def test_nothing_normalizes_to_nothing():
    assert TimeframeAPI.normalize(None) == ""
    assert TimeframeAPI.normalize("") == ""