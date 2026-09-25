import time
from datetime import timedelta

import pytest
from twisted.internet import reactor
from twisted.internet.threads import blockingCallFromThread

import Library.Market
import Library.Portfolio
from Library.Credential import VaultAPI
from Library.Database.Dataframe import pl
from Library.Spotware import SpotwareAPI
from Library.Utility.Datetime import utc_now

LABEL = "Quant Live Suite"

@pytest.fixture(scope="module")
def live(request):
    if not request.config.getoption("--spotware"): pytest.skip("The live suite runs only with --spotware")
    vault = VaultAPI(database="Quant")
    values = vault.resolve(service="Spotware", name="cTrader ID", by=vault.administrator())
    if values is None: pytest.skip("No Spotware · cTrader ID credential in the Quant vault")
    demos = [account for account in values["Accounts"] if not account["Live"] and account.get("Currency") == "EUR"]
    if not demos: pytest.skip("No EUR demo account reachable by the stored token")
    account = int(demos[0]["AccountId"])
    api = SpotwareAPI.of(values, account=account)
    assert api._host_ == "demo.ctraderapi.com"
    with api:
        listed = api.portfolio.accounts()
        assert not bool(listed.filter(pl.col("AccountID") == account)["IsLive"][0])
        yield api, account

@pytest.fixture(scope="module")
def eurusd(live):
    api, _ = live
    tickers = api.universe.tickers()
    return int(tickers.filter(pl.col("Ticker") == "EURUSD")["Symbol"][0])

def _ours_(api) -> tuple:
    response = api._request_("ProtoOAReconcileReq")
    return {position.positionId for position in response.position if position.tradeData.label == LABEL}, {order.orderId for order in response.order if order.tradeData.label == LABEL}

def test_the_account_is_a_demo_account(live):
    api, account = live
    frame = api.portfolio.account()
    assert frame["AccountID"][0] == account and frame["MoneyDigits"][0] >= 0

def test_the_universe_describes_eurusd(live, eurusd):
    api, _ = live
    spec = api.universe.ticker(eurusd)
    assert spec["Digits"][0] == 5 and spec["PipPosition"][0] == 4 and spec["MinVolume"][0] > 0
    assert len(api.universe.assets()) and len(api.universe.classes()) and len(api.universe.categories())

def test_historical_ticks_page_in_order_without_shared_milliseconds(live, eurusd):
    api, _ = live
    now = utc_now()
    for quote in ("Bid", "Ask"):
        frame = api.market.ticks(eurusd, now - timedelta(hours=2), quote=quote)
        assert len(frame) > 0 and frame["Timestamp"].is_sorted() and frame["Timestamp"].n_unique() == len(frame)

def test_bars_are_labelled_by_their_own_open_in_utc(live, eurusd):
    api, _ = live
    daily = api.market.bars(eurusd, utc_now() - timedelta(days=30), timeframe="D1")
    assert {(stamp.hour, stamp.minute) for stamp in daily["Timestamp"]} <= {(21, 0), (22, 0)}
    hourly = api.market.bars(eurusd, utc_now() - timedelta(days=2), timeframe="H1")
    assert all(stamp.minute == 0 for stamp in hourly["Timestamp"])

def test_depth_answers(live, eurusd):
    api, _ = live
    assert len(api.market.depth(eurusd, timeout=10)) > 0

def test_live_spots_carry_a_server_timestamp(live, eurusd):
    api, _ = live
    spots = []
    assert api.streaming.ticks(eurusd, spots.append, limit=5, timeout=60) == 5
    assert all(row["Timestamp"] is not None for row in spots)

def test_live_bars_open_their_own_spot_subscription(live, eurusd):
    api, _ = live
    bars = []
    assert api.streaming.bars(eurusd, "M1", bars.append, limit=1, timeout=60) == 1
    assert bars[0]["Timeframe"] == "M1"

def test_an_execution_round_trip_leaves_nothing_open(live, eurusd):
    api, _ = live
    minimum = float(api.universe.ticker(eurusd)["MinVolume"][0])
    bid = float(api.market.ticks(eurusd, utc_now() - timedelta(minutes=10), quote="Bid")["Bid"][-1])
    session = utc_now() - timedelta(seconds=30)
    try:
        opened = api.execution.market_buy_order(eurusd, 2 * minimum, label=LABEL)
        buy = opened["PositionID"][0]
        assert buy is not None
        time.sleep(1.5)
        entry = float(api.portfolio.position(buy)["EntryPrice"][0])
        api.execution.modify_position(buy, stop_loss=round(entry - 0.01, 5), take_profit=round(entry + 0.01, 5))
        api.execution.close_position(buy, volume=minimum)
        time.sleep(1.5)
        assert api.portfolio.position(buy)["Volume"][0] == minimum
        api.execution.close_position(buy, volume=minimum)
        pending = [api.execution.limit_buy_order(eurusd, minimum, round(bid * 0.95, 5), label=LABEL)["OrderID"][0], api.execution.stop_buy_order(eurusd, minimum, round(bid * 1.05, 5), label=LABEL)["OrderID"][0], api.execution.stop_limit_buy_order(eurusd, minimum, round(bid * 1.05, 5), 100, label=LABEL)["OrderID"][0]]
        assert None not in pending
        api.execution.modify_order(pending[0], limit_price=round(bid * 0.94, 5))
        api.execution.close_order(pending)
        time.sleep(2)
        trades = api.portfolio.trades(session)
        ours = trades.filter(pl.col("PositionID") == buy)
        assert len(ours) == 2 and set(ours["Direction"].to_list()) == {"Buy"}
        paged = api.portfolio.trades(session, rows=1)
        assert sorted(paged["TradeID"].to_list()) == sorted(trades["TradeID"].to_list())
    finally:
        time.sleep(1.5)
        positions, orders = _ours_(api)
        for position in positions: api.execution.close_position(position)
        if orders: api.execution.close_order(sorted(orders))
    time.sleep(1.5)
    assert _ours_(api) == (set(), set())

def test_a_dropped_socket_restores_the_session(live):
    api, _ = live
    before = api._connection_._protocol_
    blockingCallFromThread(reactor, api._connection_.drop)
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline and not (api._ready_.is_set() and api._connection_._protocol_ not in (None, before)): time.sleep(0.2)
    assert api._connection_._protocol_ is not before and api._ready_.is_set()
    assert len(api.portfolio.account()) == 1