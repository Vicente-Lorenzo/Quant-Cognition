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

def _demos_(config) -> list:
    if not config.getoption("--spotware"): return []
    vault = VaultAPI(database="Quant")
    values = vault.resolve(service="Spotware", name="cTrader ID", by=vault.administrator())
    return [(int(account["AccountId"]), account.get("Currency")) for account in (values or {}).get("Accounts") or [] if not account["Live"]]

def pytest_generate_tests(metafunc):
    if "live" not in metafunc.fixturenames: return
    demos = _demos_(metafunc.config)
    ids = [f"{currency} {sum(1 for _, other in demos[:index] if other == currency) + 1}" for index, (_, currency) in enumerate(demos)]
    metafunc.parametrize("live", demos or [None], ids=ids or ["None"], indirect=True, scope="module")

@pytest.fixture(scope="module")
def live(request):
    if not request.config.getoption("--spotware"): pytest.skip("The live suite runs only with --spotware")
    if request.param is None: pytest.skip("No demo account reachable by the stored token")
    vault = VaultAPI(database="Quant")
    values = vault.resolve(service="Spotware", name="cTrader ID", by=vault.administrator())
    account = request.param[0]
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

@pytest.fixture(scope="module")
def trading(live):
    api, _ = live
    tickers = api.universe.tickers()
    for name in ("EURUSD", "BTCUSD"):
        symbol = int(tickers.filter(pl.col("Ticker") == name)["Symbol"][0])
        recent = api.market.ticks(symbol, utc_now() - timedelta(minutes=10), quote="Bid")
        if len(recent): return symbol, float(recent["Bid"][-1]), int(api.universe.ticker(symbol)["Digits"][0])
    pytest.skip("Markets closed · no EURUSD or BTCUSD tick in the last ten minutes")

def _flatten_(api) -> None:
    time.sleep(1.5)
    positions, orders = _ours_(api)
    for position in positions: api.execution.close_position(position)
    if orders: api.execution.close_order(sorted(orders))
    time.sleep(1.5)

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
    last = api.market.bars(eurusd, utc_now() - timedelta(days=7), timeframe="H1")["Timestamp"][-1]
    for quote in ("Bid", "Ask"):
        frame = api.market.ticks(eurusd, last - timedelta(hours=2), last + timedelta(hours=1), quote=quote)
        assert len(frame) > 0 and frame["Timestamp"].is_sorted() and frame["Timestamp"].n_unique() == len(frame)

def test_bars_are_labelled_by_their_own_open_in_utc(live, eurusd):
    api, _ = live
    daily = api.market.bars(eurusd, utc_now() - timedelta(days=30), timeframe="D1")
    assert {(stamp.hour, stamp.minute) for stamp in daily["Timestamp"]} <= {(21, 0), (22, 0)}
    hourly = api.market.bars(eurusd, utc_now() - timedelta(days=2), timeframe="H1")
    assert all(stamp.minute == 0 for stamp in hourly["Timestamp"])

def test_depth_answers(live, trading):
    api, _ = live
    symbol, _, _ = trading
    assert len(api.market.depth(symbol, timeout=10)) > 0

def test_live_spots_carry_a_server_timestamp(live, trading):
    api, _ = live
    symbol, _, _ = trading
    spots = []
    assert api.streaming.ticks(symbol, spots.append, limit=5, timeout=60) == 5
    assert all(row["Timestamp"] is not None for row in spots)

def test_live_bars_open_their_own_spot_subscription(live, trading):
    api, _ = live
    symbol, _, _ = trading
    bars = []
    assert api.streaming.bars(symbol, "M1", bars.append, limit=1, timeout=60) == 1
    assert bars[0]["Timeframe"] == "M1"

def test_an_execution_round_trip_leaves_nothing_open(live, trading):
    api, _ = live
    symbol, bid, digits = trading
    minimum = float(api.universe.ticker(symbol)["MinVolume"][0])
    session = utc_now() - timedelta(seconds=30)
    try:
        opened = api.execution.market_buy_order(symbol, 2 * minimum, label=LABEL)
        buy = opened["PositionID"][0]
        assert buy is not None
        time.sleep(1.5)
        entry = float(api.portfolio.position(buy)["EntryPrice"][0])
        api.execution.modify_position(buy, stop_loss=round(entry * 0.99, digits), take_profit=round(entry * 1.01, digits))
        api.execution.close_position(buy, volume=minimum)
        time.sleep(1.5)
        assert api.portfolio.position(buy)["Volume"][0] == minimum
        api.execution.close_position(buy, volume=minimum)
        pending = [api.execution.limit_buy_order(symbol, minimum, round(bid * 0.95, digits), label=LABEL)["OrderID"][0], api.execution.stop_buy_order(symbol, minimum, round(bid * 1.05, digits), label=LABEL)["OrderID"][0], api.execution.stop_limit_buy_order(symbol, minimum, round(bid * 1.05, digits), 100, label=LABEL)["OrderID"][0]]
        assert None not in pending
        api.execution.modify_order(pending[0], limit_price=round(bid * 0.94, digits))
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

def test_every_reader_answers(live):
    api, account = live
    start = utc_now() - timedelta(days=30)
    assert len(api.universe.tickers()) > 800 and len(api.universe.tickers(archived=True)) >= len(api.universe.tickers())
    for frame in (api.universe.assets(), api.universe.classes(), api.universe.categories(), api.universe.catalog()): assert len(frame) > 0
    for frame in (api.portfolio.positions(), api.portfolio.orders(), api.portfolio.pnl(), api.portfolio.orders(start), api.portfolio.trades(start), api.portfolio.deals(start), api.portfolio.cashflow(start)): assert frame is not None and hasattr(frame, "columns")
    stop = api.universe.changes(lambda changed: None)
    stop()

def test_a_round_trip_moves_the_balance_by_exactly_its_net_pnl(live, trading):
    api, _ = live
    symbol, _, _ = trading
    minimum = float(api.universe.ticker(symbol)["MinVolume"][0])
    info = api.portfolio.account()
    before, digits = float(info["Balance"][0]), int(info["MoneyDigits"][0])
    session = utc_now() - timedelta(seconds=5)
    try:
        position = api.execution.market_buy_order(symbol, minimum, label=LABEL)["PositionID"][0]
        time.sleep(1.5)
        assert float(api.portfolio.account()["Balance"][0]) == before
        api.execution.close_position(position)
    finally:
        _flatten_(api)
    after = float(api.portfolio.account()["Balance"][0])
    trade = api.portfolio.trades(session).filter(pl.col("PositionID") == position)
    assert len(trade) == 1
    assert round(after - before, digits) == round(float(trade["NetPnL"][0]), digits) and round(float(trade["ExitBalance"][0]), digits) == round(after, digits)

def test_the_sell_side_and_every_order_type_round_trip(live, trading):
    api, _ = live
    symbol, bid, digits = trading
    spec = api.universe.ticker(symbol)
    minimum, pip = float(spec["MinVolume"][0]), 10 ** -int(spec["PipPosition"][0])
    expiry = (utc_now() + timedelta(days=2)).replace(microsecond=0)
    try:
        sold = api.execution.market_sell_order(symbol, minimum, relative_stop_loss=100 * pip, relative_take_profit=100 * pip, label=LABEL)["PositionID"][0]
        time.sleep(1.5)
        held = api.portfolio.position(sold)
        assert held["Direction"][0] == "Sell" and held["StopLossPrice"][0] > held["EntryPrice"][0] > held["TakeProfitPrice"][0]
        api.execution.close_position(sold)
        ranged = [api.execution.range_buy_order(symbol, minimum, round(bid, digits), 100, label=LABEL)["PositionID"][0], api.execution.range_sell_order(symbol, minimum, round(bid, digits), 100, label=LABEL)["PositionID"][0]]
        assert None not in ranged
        _flatten_(api)
        limit = api.execution.limit_sell_order(symbol, minimum, round(bid * 1.05, digits), stop_loss=round(bid * 1.07, digits), take_profit=round(bid * 1.03, digits), time_in_force="GoodTillDate", expiration=expiry, label=LABEL)["OrderID"][0]
        pending = [limit, api.execution.stop_sell_order(symbol, minimum, round(bid * 0.95, digits), label=LABEL)["OrderID"][0], api.execution.stop_limit_sell_order(symbol, minimum, round(bid * 0.95, digits), 100, label=LABEL)["OrderID"][0]]
        assert None not in pending
        api.execution.modify_order(limit, limit_price=round(bid * 1.06, digits))
        api.execution.modify_order(pending[1], volume=2 * minimum)
        time.sleep(1.5)
        order = api.portfolio.order(limit)
        assert (order["LimitPrice"][0], order["StopLossPrice"][0], order["TakeProfitPrice"][0]) == (round(bid * 1.06, digits), round(bid * 1.07, digits), round(bid * 1.03, digits))
        assert order["ExpirationTimestamp"][0] == expiry and order["TimeInForce"][0] == "GoodTillDate"
        assert api.portfolio.order(pending[1])["Volume"][0] == 2 * minimum
        api.execution.close_order(pending)
    finally:
        _flatten_(api)
    assert _ours_(api) == (set(), set())

def test_a_dropped_socket_restores_the_session(live):
    api, _ = live
    before = api._connection_._protocol_
    blockingCallFromThread(reactor, api._connection_.drop)
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline and not (api._ready_.is_set() and api._connection_._protocol_ not in (None, before)): time.sleep(0.2)
    assert api._connection_._protocol_ is not before and api._ready_.is_set()
    assert len(api.portfolio.account()) == 1