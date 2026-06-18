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