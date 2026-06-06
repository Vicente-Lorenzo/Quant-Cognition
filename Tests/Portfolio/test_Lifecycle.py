import pytest
from datetime import datetime, timedelta
from Library.Universe.Contract import ContractAPI
from Library.Universe.Security import SecurityAPI
from Library.Market.Tick import TickAPI
from Library.Market.Bar import BarAPI
from Library.Market.Price import Direction
from Library.Portfolio.Account import AccountAPI
from Library.Portfolio.Portfolio import PortfolioAPI
from Library.Portfolio.Position import PositionAPI, PositionType
from Library.Portfolio.Trade import TradeAPI
from Library.Portfolio.PnL import PnLAPI
from Library.Portfolio.Order import OrderAPI, OrderType, OrderStatus, TimeInForce

ENTRY_DT = datetime(2026, 5, 1, 12, 0, 0)
EXIT_DT = datetime(2026, 5, 1, 14, 0, 0)

@pytest.fixture
def env():
    contract = ContractAPI(PipSize=0.0001, PointSize=0.00001, Digits=5, LotSize=100000)
    security = SecurityAPI()
    security._contract_ = contract
    account = AccountAPI(Balance=10000.0)
    portfolio = PortfolioAPI()
    portfolio._account_ = account
    portfolio._security_ = security
    return {"account": account, "security": security, "contract": contract, "portfolio": portfolio}

def make_position(env, uid=1001, direction=Direction.Buy, volume=100000.0, entry=1.0500, sl=None, tp=None):
    return PositionAPI(
        UID=uid,
        Type=PositionType.Normal,
        Direction=direction,
        Volume=volume,
        Quantity=1.0,
        Security=env["security"],
        EntryTimestamp=ENTRY_DT,
        EntryPrice=entry,
        StopLossPrice=sl,
        TakeProfitPrice=tp,
        GrossPnL=0.0,
        CommissionPnL=-2.0,
        SwapPnL=0.0,
        NetPnL=0.0,
    )

def make_tick(env, ts, ask, bid):
    return TickAPI(Security=env["security"], Timestamp=ts, Ask=ask, Bid=bid)

def make_bar(env, ts, open_ask, open_bid, high_ask, high_bid, low_ask, low_bid, close_ask, close_bid):
    bar = BarAPI(Security=env["security"], Timestamp=ts)
    bar._open_tick_ = make_tick(env, ts, open_ask, open_bid)
    bar._high_tick_ = make_tick(env, ts, high_ask, high_bid)
    bar._low_tick_ = make_tick(env, ts, low_ask, low_bid)
    bar._close_tick_ = make_tick(env, ts, close_ask, close_bid)
    return bar

def make_trade(env, uid=2001, direction=Direction.Buy, volume=100000.0, entry=1.0500, exit_price=1.0550, net=500.0, gross=502.0, comm=-2.0, exit_ts=EXIT_DT):
    return TradeAPI(
        UID=uid,
        Type=PositionType.Normal,
        Direction=direction,
        Volume=volume,
        Quantity=1.0,
        Security=env["security"],
        EntryTimestamp=ENTRY_DT,
        EntryPrice=entry,
        ExitTimestamp=exit_ts,
        ExitPrice=exit_price,
        GrossPnL=gross,
        CommissionPnL=comm,
        SwapPnL=0.0,
        NetPnL=net,
    )

def test_open_position_initializes_entry_and_mid_balance(env):
    pf = env["portfolio"]
    pos = make_position(env)
    pf.open_position(order_uid=999, position=pos)
    assert pos.EntryBalance == 10000.0
    assert pos.MidBalance == 10000.0
    assert pos.UID in pf._positions_

def test_open_position_consumes_pending_order(env):
    pf = env["portfolio"]
    order = OrderAPI(UID=42, Direction=Direction.Buy, OrderType=OrderType.Market, OrderStatus=OrderStatus.Accepted, TimeInForce=TimeInForce.GoodTillCancel, Volume=100000.0, Security=env["security"])
    pf.open_order(order)
    assert 42 in pf._orders_
    pos = make_position(env)
    pf.open_position(order_uid=42, position=pos)
    assert 42 not in pf._orders_

def test_update_data_tick_long_creates_runup_drawdown(env):
    pf = env["portfolio"]
    pos = make_position(env, direction=Direction.Buy, entry=1.0500)
    pf.open_position(0, pos)
    tick = make_tick(env, ENTRY_DT + timedelta(minutes=5), ask=1.0560, bid=1.0555)
    pf.update_data(tick)
    assert pos.MaxEquityRunupPrice is not None and pos.MaxEquityRunupPrice.Price == pytest.approx(1.0555)
    assert pos.MaxEquityDrawdownPrice is not None and pos.MaxEquityDrawdownPrice.Price == pytest.approx(1.0555)
    assert pos.MaxEquityRunupPnL is not None and pos.MaxEquityRunupPnL.PnL is not None
    assert pos.MaxEquityDrawdownPnL is not None and pos.MaxEquityDrawdownPnL.PnL is not None
    assert pos.NetPnL.PnL == pytest.approx((1.0555 - 1.0500) * 100000.0 - 2.0)

def test_update_data_tick_short_uses_ask(env):
    pf = env["portfolio"]
    pos = make_position(env, direction=Direction.Sell, entry=1.0500)
    pf.open_position(0, pos)
    tick = make_tick(env, ENTRY_DT + timedelta(minutes=5), ask=1.0480, bid=1.0475)
    pf.update_data(tick)
    assert pos.NetPnL.PnL == pytest.approx((1.0500 - 1.0480) * 100000.0 - 2.0)
    assert pos.MaxEquityRunupPrice.Price == pytest.approx(1.0480)
    assert pos.MaxEquityDrawdownPrice.Price == pytest.approx(1.0480)

def test_update_data_running_extremes_track_correctly(env):
    pf = env["portfolio"]
    pos = make_position(env, direction=Direction.Buy, entry=1.0500)
    pf.open_position(0, pos)
    pf.update_data(make_tick(env, ENTRY_DT + timedelta(minutes=1), ask=1.0560, bid=1.0555))
    pf.update_data(make_tick(env, ENTRY_DT + timedelta(minutes=2), ask=1.0480, bid=1.0475))
    pf.update_data(make_tick(env, ENTRY_DT + timedelta(minutes=3), ask=1.0520, bid=1.0515))
    assert pos.MaxEquityRunupPrice.Price == pytest.approx(1.0555)
    assert pos.MaxEquityDrawdownPrice.Price == pytest.approx(1.0475)
    assert pos.MaxEquityRunupPnL.PnL > 0
    assert pos.MaxEquityDrawdownPnL.PnL < 0

def test_update_data_bar_uses_high_low_extremes_long(env):
    pf = env["portfolio"]
    pos = make_position(env, direction=Direction.Buy, entry=1.0500)
    pf.open_position(0, pos)
    bar = make_bar(env, ENTRY_DT + timedelta(minutes=10),
                   open_ask=1.0510, open_bid=1.0508,
                   high_ask=1.0600, high_bid=1.0598,
                   low_ask=1.0420, low_bid=1.0418,
                   close_ask=1.0530, close_bid=1.0528)
    pf.update_data(bar)
    assert pos.MaxEquityRunupPrice.Price == pytest.approx(1.0598)
    assert pos.MaxEquityDrawdownPrice.Price == pytest.approx(1.0418)
    assert pos.NetPnL.PnL == pytest.approx((1.0528 - 1.0500) * 100000.0 - 2.0)

def test_update_data_bar_uses_high_low_extremes_short(env):
    pf = env["portfolio"]
    pos = make_position(env, direction=Direction.Sell, entry=1.0500)
    pf.open_position(0, pos)
    bar = make_bar(env, ENTRY_DT + timedelta(minutes=10),
                   open_ask=1.0510, open_bid=1.0508,
                   high_ask=1.0600, high_bid=1.0598,
                   low_ask=1.0420, low_bid=1.0418,
                   close_ask=1.0530, close_bid=1.0528)
    pf.update_data(bar)
    assert pos.MaxEquityRunupPrice.Price == pytest.approx(1.0420)
    assert pos.MaxEquityDrawdownPrice.Price == pytest.approx(1.0600)

def test_update_data_skips_positions_without_netpnl(env):
    pf = env["portfolio"]
    pos = PositionAPI(UID=1, Type=PositionType.Normal, Direction=Direction.Buy, Volume=100000.0, Security=env["security"], EntryTimestamp=ENTRY_DT, EntryPrice=1.0500)
    pf._positions_[1] = pos
    tick = make_tick(env, ENTRY_DT + timedelta(minutes=1), ask=1.0560, bid=1.0555)
    pf.update_data(tick)
    assert pos.NetPnL is None

def test_close_position_full_propagates_state(env):
    pf = env["portfolio"]
    pos = make_position(env, direction=Direction.Buy, entry=1.0500)
    pf.open_position(0, pos)
    for ask, bid in [(1.0560, 1.0555), (1.0480, 1.0475), (1.0520, 1.0515)]:
        pf.update_data(make_tick(env, ENTRY_DT + timedelta(minutes=1), ask=ask, bid=bid))
    trade = make_trade(env, exit_price=1.0550, net=498.0)
    pf.close_position(pos.UID, None, trade)
    assert pos.UID not in pf._positions_
    assert trade in pf._trades_
    assert trade.MaxEquityRunupPrice is not None and trade.MaxEquityRunupPrice.Price == pytest.approx(1.0555)
    assert trade.MaxEquityDrawdownPrice is not None and trade.MaxEquityDrawdownPrice.Price == pytest.approx(1.0475)
    assert trade.MaxEquityRunupPnL is not None
    assert trade.MaxEquityDrawdownPnL is not None
    assert trade.EntryBalance == 10000.0
    assert trade.ExitBalance == pytest.approx(10498.0)
    assert trade.MidBalance == pytest.approx(10498.0)
    assert env["account"].Balance == pytest.approx(10498.0)
    assert trade.Position is pos

def test_close_position_inherits_entry_state_from_position(env):
    pf = env["portfolio"]
    pos = make_position(env, direction=Direction.Buy, entry=1.0500)
    pf.open_position(0, pos)
    trade = TradeAPI(UID=2001, Volume=100000.0, ExitTimestamp=EXIT_DT, ExitPrice=1.0550, GrossPnL=502.0, CommissionPnL=-2.0, SwapPnL=0.0, NetPnL=500.0)
    pf.close_position(pos.UID, None, trade)
    assert trade.Direction == Direction.Buy
    assert trade.Type == PositionType.Normal
    assert trade.Security is env["security"]
    assert trade.EntryTimestamp.DateTime == ENTRY_DT
    assert trade.EntryPrice.Price == pytest.approx(1.0500)

def test_close_position_exit_price_extends_extremes(env):
    pf = env["portfolio"]
    pos = make_position(env, direction=Direction.Buy, entry=1.0500)
    pf.open_position(0, pos)
    pf.update_data(make_tick(env, ENTRY_DT + timedelta(minutes=1), ask=1.0510, bid=1.0508))
    trade = make_trade(env, exit_price=1.0700, net=1998.0)
    pf.close_position(pos.UID, None, trade)
    assert trade.MaxEquityRunupPrice.Price == pytest.approx(1.0700)

def test_close_position_exit_pnl_extends_extremes(env):
    pf = env["portfolio"]
    pos = make_position(env, direction=Direction.Buy, entry=1.0500)
    pf.open_position(0, pos)
    pf.update_data(make_tick(env, ENTRY_DT + timedelta(minutes=1), ask=1.0510, bid=1.0508))
    trade = make_trade(env, exit_price=1.0700, net=1998.0)
    pf.close_position(pos.UID, None, trade)
    assert trade.MaxEquityRunupPnL.PnL == pytest.approx(1998.0)

def test_close_position_partial_single_partial(env):
    pf = env["portfolio"]
    pos = make_position(env, direction=Direction.Buy, entry=1.0500, volume=100000.0)
    pf.open_position(0, pos)
    trade = make_trade(env, volume=50000.0, exit_price=1.0520, net=20.0, gross=22.0, comm=-2.0)
    remaining = PositionAPI(UID=pos.UID, Volume=50000.0)
    pf.close_position(pos.UID, remaining, trade)
    assert pos.UID in pf._positions_
    assert pf._positions_[pos.UID] is remaining
    assert trade.EntryBalance == 10000.0
    assert trade.MidBalance == pytest.approx(10020.0)
    assert trade.ExitBalance == pytest.approx(10020.0)
    assert remaining.EntryBalance == 10000.0
    assert remaining.MidBalance == pytest.approx(10020.0)
    assert remaining.Volume == 50000.0
    assert env["account"].Balance == pytest.approx(10020.0)

def test_close_position_partial_three_step_user_scenario(env):
    pf = env["portfolio"]
    pos = make_position(env, direction=Direction.Buy, entry=1.0500, volume=100000.0)
    pf.open_position(0, pos)
    trade1 = make_trade(env, uid=1, volume=50000.0, exit_price=1.0520, net=20.0)
    remaining1 = PositionAPI(UID=pos.UID, Volume=50000.0)
    pf.close_position(pos.UID, remaining1, trade1)
    assert trade1.EntryBalance == 10000.0
    assert trade1.MidBalance == pytest.approx(10020.0)
    assert trade1.ExitBalance == pytest.approx(10020.0)
    trade2 = make_trade(env, uid=2, volume=30000.0, exit_price=1.0510, net=10.0)
    remaining2 = PositionAPI(UID=pos.UID, Volume=20000.0)
    pf.close_position(pos.UID, remaining2, trade2)
    assert trade2.EntryBalance == 10000.0
    assert trade2.MidBalance == pytest.approx(10030.0)
    assert trade2.ExitBalance == pytest.approx(10030.0)
    trade3 = make_trade(env, uid=3, volume=20000.0, exit_price=1.0505, net=5.0)
    pf.close_position(pos.UID, None, trade3)
    assert trade3.EntryBalance == 10000.0
    assert trade3.MidBalance == pytest.approx(10035.0)
    assert trade3.ExitBalance == pytest.approx(10035.0)
    assert env["account"].Balance == pytest.approx(10035.0)
    assert pos.UID not in pf._positions_
    assert len(pf._trades_) == 3
    assert all(t.EntryBalance == 10000.0 for t in pf._trades_)

def test_close_position_partial_preserves_runup_drawdown_through_partials(env):
    pf = env["portfolio"]
    pos = make_position(env, direction=Direction.Buy, entry=1.0500, volume=100000.0)
    pf.open_position(0, pos)
    pf.update_data(make_tick(env, ENTRY_DT + timedelta(minutes=1), ask=1.0560, bid=1.0555))
    pf.update_data(make_tick(env, ENTRY_DT + timedelta(minutes=2), ask=1.0440, bid=1.0438))
    runup_before = pos.MaxEquityRunupPrice.Price
    drawdown_before = pos.MaxEquityDrawdownPrice.Price
    trade1 = make_trade(env, uid=1, volume=50000.0, exit_price=1.0520, net=20.0)
    remaining = PositionAPI(UID=pos.UID, Volume=50000.0)
    pf.close_position(pos.UID, remaining, trade1)
    assert remaining.MaxEquityRunupPrice is not None and remaining.MaxEquityRunupPrice.Price == runup_before
    assert remaining.MaxEquityDrawdownPrice is not None and remaining.MaxEquityDrawdownPrice.Price == drawdown_before
    assert trade1.MaxEquityRunupPrice.Price == runup_before
    assert trade1.MaxEquityDrawdownPrice.Price == drawdown_before

def test_close_position_loss_decreases_account_and_balances(env):
    pf = env["portfolio"]
    pos = make_position(env, direction=Direction.Buy, entry=1.0500)
    pf.open_position(0, pos)
    trade = make_trade(env, exit_price=1.0450, net=-502.0, gross=-500.0)
    pf.close_position(pos.UID, None, trade)
    assert env["account"].Balance == pytest.approx(9498.0)
    assert trade.MidBalance == pytest.approx(9498.0)
    assert trade.ExitBalance == pytest.approx(9498.0)

def test_modify_position_preserves_runup_drawdown_and_balance(env):
    pf = env["portfolio"]
    pos = make_position(env, direction=Direction.Buy, entry=1.0500)
    pf.open_position(0, pos)
    pf.update_data(make_tick(env, ENTRY_DT + timedelta(minutes=1), ask=1.0560, bid=1.0555))
    pf.update_data(make_tick(env, ENTRY_DT + timedelta(minutes=2), ask=1.0440, bid=1.0438))
    runup_before = pos.MaxEquityRunupPrice.Price
    drawdown_before = pos.MaxEquityDrawdownPrice.Price
    midbal_before = pos.MidBalance
    new_pos = PositionAPI(UID=pos.UID, StopLossPrice=1.0400)
    pf.modify_position(new_pos)
    assert pf._positions_[pos.UID] is new_pos
    assert new_pos.MaxEquityRunupPrice.Price == runup_before
    assert new_pos.MaxEquityDrawdownPrice.Price == drawdown_before
    assert new_pos.EntryBalance == 10000.0
    assert new_pos.MidBalance == midbal_before
    assert new_pos.Direction == Direction.Buy
    assert new_pos.EntryPrice.Price == pytest.approx(1.0500)

def test_modify_position_keeps_explicit_overrides(env):
    pf = env["portfolio"]
    pos = make_position(env, direction=Direction.Buy, entry=1.0500, volume=100000.0)
    pf.open_position(0, pos)
    new_pos = PositionAPI(UID=pos.UID, Volume=50000.0)
    pf.modify_position(new_pos)
    assert new_pos.Volume == 50000.0

def test_open_modify_close_order_lifecycle(env):
    pf = env["portfolio"]
    o = OrderAPI(UID=7, Direction=Direction.Buy, OrderType=OrderType.Limit, OrderStatus=OrderStatus.Accepted, TimeInForce=TimeInForce.GoodTillCancel, Volume=100000.0, Security=env["security"], LimitPrice=1.0400)
    pf.open_order(o)
    assert pf._orders_[7] is o
    o2 = OrderAPI(UID=7, Direction=Direction.Buy, OrderType=OrderType.Limit, OrderStatus=OrderStatus.Accepted, TimeInForce=TimeInForce.GoodTillCancel, Volume=100000.0, Security=env["security"], LimitPrice=1.0410)
    pf.modify_order(o2)
    assert pf._orders_[7] is o2
    pf.close_order(7)
    assert 7 not in pf._orders_

def test_portfolio_aggregate_realized_unrealized_net(env):
    pf = env["portfolio"]
    pos = make_position(env, direction=Direction.Buy, entry=1.0500)
    pf.open_position(0, pos)
    pf.update_data(make_tick(env, ENTRY_DT + timedelta(minutes=1), ask=1.0560, bid=1.0555))
    unrealized_open = pf.UnrealizedPnL
    trade = make_trade(env, exit_price=1.0550, net=498.0)
    pf.close_position(pos.UID, None, trade)
    pos2 = make_position(env, uid=1002, direction=Direction.Sell, entry=1.0600)
    pf.open_position(0, pos2)
    pf.update_data(make_tick(env, ENTRY_DT + timedelta(minutes=10), ask=1.0590, bid=1.0588))
    assert pf.RealizedPnL == pytest.approx(498.0)
    assert pf.UnrealizedPnL == pos2.NetPnL.PnL
    assert pf.NetPnL == pytest.approx(pf.RealizedPnL + pf.UnrealizedPnL)
    assert unrealized_open != 0

def test_position_annualized_metrics_via_netpnl(env):
    pf = env["portfolio"]
    pos = make_position(env, direction=Direction.Buy, entry=1.0500)
    pf.open_position(0, pos)
    pf.update_data(make_tick(env, ENTRY_DT + timedelta(days=10), ask=1.0700, bid=1.0698))
    assert pos.NetPnL.Duration == pytest.approx(10 * 86400.0)
    assert pos.NetPnL.Reference == pytest.approx(10000.0)
    assert pos.AnnualizedReturn is not None
    assert pos.AnnualizedLogReturn is not None
    assert pos.AnnualizedPercentage is not None
    assert pos.AnnualizedLogPercentage is not None

def test_pnl_returns_basic():
    p = PnLAPI(PnL=100.0, Reference=10000.0, Duration=86400.0)
    assert p.Return == pytest.approx(0.01)
    assert p.Percentage == pytest.approx(1.0)
    assert p.LogReturn is not None
    assert p.AnnualizedReturn is not None

def test_pnl_returns_handle_none():
    p = PnLAPI(PnL=100.0)
    assert p.Return is None
    assert p.LogReturn is None
    assert p.Percentage is None
    assert p.AnnualizedReturn is None

def test_close_position_when_position_missing_still_records_trade(env):
    pf = env["portfolio"]
    trade = make_trade(env, net=500.0)
    pf.close_position(99999, None, trade)
    assert trade in pf._trades_
    assert env["account"].Balance == 10000.0
