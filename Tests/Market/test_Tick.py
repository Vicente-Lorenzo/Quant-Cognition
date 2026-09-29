from datetime import datetime, timedelta

from Library.Market.Tick import TickAPI

def test_encode_matches_bit_layout():
    sec, ts = 100, datetime(2023, 1, 1, 12, 0, 0)
    ms = int((ts - datetime(1970, 1, 1)).total_seconds() * 1000)
    expected = (sec << 42) | ms
    assert TickAPI.encode(sec, ts) == expected
    assert TickAPI(sec, ts, Ask=1.1, Bid=1.0).UID == expected

def test_encode_bijection_no_collision():
    base, seen = datetime(2023, 1, 1), {}
    for security in (1, 2, 100, 2000):
        for k in range(2000):
            ts = base + timedelta(milliseconds=k * 137)
            uid = TickAPI.encode(security, ts)
            assert uid not in seen
            seen[uid] = (security, ts)
    assert TickAPI.encode(100, base) == TickAPI.encode(100, base)

def test_encode_monotonic_in_time():
    s, t0 = 7, datetime(2023, 1, 1, 0, 0, 0)
    assert TickAPI.encode(s, t0 + timedelta(milliseconds=1)) > TickAPI.encode(s, t0)

def test_encode_security_isolation():
    later, earlier = datetime(2099, 12, 31, 23, 59, 59), datetime(1970, 1, 1)
    assert TickAPI.encode(10, later) < TickAPI.encode(11, earlier)

def test_uid_recomputed_on_natural_key_change():
    a, b = datetime(2023, 1, 1), datetime(2023, 1, 2)
    tick = TickAPI(5, a, Ask=1.1, Bid=1.0)
    assert tick.UID == TickAPI.encode(5, a)
    tick.Timestamp = b
    assert tick.UID == TickAPI.encode(5, b)
    tick.Security = 9
    assert tick.UID == TickAPI.encode(9, b)

def test_tick_initialization():
    now = datetime.now()
    tick = TickAPI(100, now, 1.1005, 1.1000, 2.0, 1.0, 1.0, 1.0, 1.0)
    assert tick.Security is not None
    assert tick.Security.UID == 100
    assert tick.Timestamp.DateTime == now
    assert tick.Ask.Price == 1.1005
    assert tick.Bid.Price == 1.1000
    assert tick.Volume == 2.0

def test_tick_properties():
    now = datetime.now()
    tick = TickAPI(1, now, Ask=1.1005, Bid=1.1000)
    assert tick.Mid.Price == 1.10025
    assert tick.Spread is not None
    assert round(tick.Spread.Price, 4) == 0.0005
    assert tick.InvertedAsk == 1.0 / 1.1005
    assert tick.InvertedBid == 1.0 / 1.1000