import threading
from typing import Union
import pytest
import Library.Market
import Library.Portfolio
from ctrader_open_api.messages.OpenApiMessages_pb2 import (
    ProtoOASpotEvent,
    ProtoOADepthEvent,
    ProtoOASubscribeSpotsRes,
    ProtoOAUnsubscribeSpotsRes,
    ProtoOASubscribeDepthQuotesRes,
    ProtoOAUnsubscribeDepthQuotesRes,
    ProtoOASubscribeLiveTrendbarRes,
    ProtoOAUnsubscribeLiveTrendbarRes
)
def _spot_event(symbol_id: int, bid: Union[int, None] = None, ask: Union[int, None] = None, timestamp: Union[int, None] = None):
    ev = ProtoOASpotEvent()
    ev.ctidTraderAccountId = 123
    ev.symbolId = symbol_id
    if bid is not None: ev.bid = bid
    if ask is not None: ev.ask = ask
    if timestamp is not None: ev.timestamp = timestamp
    return ev
def _depth_event(symbol_id: int, new=None, deleted=None):
    ev = ProtoOADepthEvent()
    ev.ctidTraderAccountId = 123
    ev.symbolId = symbol_id
    for qid, size, bid, ask in (new or []):
        q = ev.newQuotes.add()
        q.id = qid
        q.size = size
        if bid is not None: q.bid = bid
        if ask is not None: q.ask = ask
    for qid in (deleted or []):
        ev.deletedQuotes.append(qid)
    return ev
def _within_(function, seconds: float = 5):
    outcome = {}
    def _run_():
        try: outcome["result"] = function()
        except Exception as error: outcome["error"] = error
    worker = threading.Thread(target=_run_, daemon=True)
    worker.start()
    worker.join(timeout=seconds)
    assert not worker.is_alive()
    return outcome
def _spots_(api, *events):
    def fire(request, api):
        for ev in events: api.push(ev)
        return ProtoOASubscribeSpotsRes()
    api._responses_.append(fire)
    api._responses_.append(ProtoOAUnsubscribeSpotsRes())
    return api._message_("ProtoOASubscribeSpotsReq", symbolId=[1]), api._message_("ProtoOAUnsubscribeSpotsReq", symbolId=[1])
def test_ticks_dispatches_events(spotware):
    events = [
        _spot_event(1, bid=105000, ask=105002),
        _spot_event(1, bid=105010, ask=105012),
        _spot_event(2, bid=205000, ask=205005),
        _spot_event(1, bid=105020, ask=105022)
    ]
    def fire(request, api):
        for ev in events: api.push(ev)
        return ProtoOASubscribeSpotsRes()
    spotware._responses_.append(fire)
    spotware._responses_.append(ProtoOAUnsubscribeSpotsRes())
    received = []
    spotware.streaming.ticks(symbols=1, callback=lambda d: received.append(d), frame=False, limit=3, timeout=5)
    assert len(received) == 3
    assert all(r["Symbol"] == 1 for r in received)
    assert received[0]["Bid"] == pytest.approx(1.05)
    assert received[0]["Ask"] == pytest.approx(1.05002)
    assert received[1]["Bid"] == pytest.approx(1.0501)
    assert type(spotware._sent_[0]).__name__ == "ProtoOASubscribeSpotsReq"
    assert list(spotware._sent_[0].symbolId) == [1]
    assert type(spotware._sent_[1]).__name__ == "ProtoOAUnsubscribeSpotsReq"
def test_ticks_respects_limit(spotware):
    events = [_spot_event(1, bid=100000 + i, ask=100002 + i) for i in range(10)]
    def fire(request, api):
        for ev in events: api.push(ev)
        return ProtoOASubscribeSpotsRes()
    spotware._responses_.append(fire)
    spotware._responses_.append(ProtoOAUnsubscribeSpotsRes())
    received = []
    spotware.streaming.ticks(symbols=[1], callback=lambda d: received.append(d), frame=False, limit=4, timeout=5)
    assert len(received) == 4
def test_ticks_frame_output(spotware):
    def fire(request, api):
        api.push(_spot_event(1, bid=105000, ask=105005))
        return ProtoOASubscribeSpotsRes()
    spotware._responses_.append(fire)
    spotware._responses_.append(ProtoOAUnsubscribeSpotsRes())
    received = []
    spotware.streaming.ticks(symbols=[1], callback=lambda df: received.append(df), frame=True, limit=1, timeout=5)
    assert len(received) == 1
    df = received[0]
    assert len(df) == 1
    assert df["Symbol"][0] == 1
    assert df["Bid"][0] == pytest.approx(1.05)
def test_depth_new_and_deleted_quotes(spotware):
    def fire(request, api):
        api.push(_depth_event(1, new=[(100, 5, 105000, 105010), (101, 10, None, 105015)], deleted=[99]))
        return ProtoOASubscribeDepthQuotesRes()
    spotware._responses_.append(fire)
    spotware._responses_.append(ProtoOAUnsubscribeDepthQuotesRes())
    received = []
    spotware.streaming.depth(symbols=1, callback=lambda d: received.append(d), frame=False, limit=1, timeout=5)
    assert len(received) == 1
    rows = received[0]
    assert len(rows) == 3
    by_id = {r["Quote"]: r for r in rows}
    assert by_id[100]["Action"] == "New"
    assert by_id[100]["Bid"] == pytest.approx(1.05)
    assert by_id[101]["Bid"] is None
    assert by_id[99]["Action"] == "Deleted"
def test_bars_live_filters_by_period_and_symbol(spotware):
    def fire(request, api):
        ev = _spot_event(1)
        bar = ev.trendbar.add()
        bar.volume = 10; bar.period = 1
        bar.low = 100000; bar.deltaOpen = 500; bar.deltaHigh = 1000; bar.deltaClose = 700
        bar.utcTimestampInMinutes = 26500000
        wrong = ev.trendbar.add()
        wrong.volume = 5; wrong.period = 5
        wrong.low = 100000; wrong.deltaOpen = 0; wrong.deltaHigh = 0; wrong.deltaClose = 0
        wrong.utcTimestampInMinutes = 26500001
        api.push(ev)
        return ProtoOASubscribeLiveTrendbarRes()
    spotware._responses_.append(fire)
    spotware._responses_.append(ProtoOAUnsubscribeLiveTrendbarRes())
    received = []
    spotware.streaming.bars(symbol=1, timeframe="M1", callback=lambda d: received.append(d), frame=False, limit=1, timeout=5)
    assert len(received) == 1
    assert received[0]["Timeframe"] == "M1"
    assert received[0]["Open"] == pytest.approx(1.005)
    assert type(spotware._sent_[0]).__name__ == "ProtoOASubscribeLiveTrendbarReq"
def test_ticks_ignores_unrelated_symbols(spotware):
    def fire(request, api):
        api.push(_spot_event(99, bid=100000, ask=100002))
        api.push(_spot_event(1, bid=100000, ask=100002))
        return ProtoOASubscribeSpotsRes()
    spotware._responses_.append(fire)
    spotware._responses_.append(ProtoOAUnsubscribeSpotsRes())
    received = []
    spotware.streaming.ticks(symbols=[1], callback=lambda d: received.append(d), frame=False, limit=1, timeout=5)
    assert len(received) == 1
    assert received[0]["Symbol"] == 1
def test_ticks_raises_a_failing_callback_instead_of_hanging(spotware):
    _spots_(spotware, _spot_event(1, bid=105000, ask=105002))
    def _callback_(item): raise ValueError("boom")
    outcome = _within_(lambda: spotware.streaming.ticks(symbols=1, callback=_callback_, limit=3))
    assert isinstance(outcome.get("error"), ValueError)
    assert type(spotware._sent_[-1]).__name__ == "ProtoOAUnsubscribeSpotsReq"
def test_listen_raises_a_failing_decoder_instead_of_hanging(spotware):
    subscribe, unsubscribe = _spots_(spotware, _spot_event(1, bid=105000, ask=105002))
    def _decode_(payload): raise KeyError("decode")
    outcome = _within_(lambda: spotware._listen_(subscribe, unsubscribe, _decode_, lambda item: None, limit=1))
    assert isinstance(outcome.get("error"), KeyError)
def test_listen_stops_decoding_once_the_limit_is_reached(spotware):
    subscribe, unsubscribe = _spots_(spotware, *[_spot_event(1, bid=bid, ask=bid + 2) for bid in (105000, 105010, 105020)])
    decoded = []
    def _decode_(payload):
        decoded.append(payload.bid)
        return [payload]
    assert spotware._listen_(subscribe, unsubscribe, _decode_, lambda item: None, limit=1, timeout=5) == 1
    assert decoded == [105000]
def test_listen_counts_items_until_the_limit_across_a_multi_item_message(spotware):
    subscribe, unsubscribe = _spots_(spotware, _spot_event(1, bid=105000, ask=105002))
    received = []
    assert spotware._listen_(subscribe, unsubscribe, lambda payload: [1, 2, 3], received.append, limit=2, timeout=5) == 2
    assert received == [1, 2]