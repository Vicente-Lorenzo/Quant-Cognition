from datetime import datetime, timedelta

import pytest

from Library.Market.Price import Direction
from Library.Portfolio.Position import PositionType
from Library.Portfolio.Trade import TradeAPI
from Library.Protocol.Action import OpenBuyPositionActionAPI, OpenSellPositionActionAPI
from Library.Protocol.Update import UpdateID
from Tests.System.test_Netting import ASK, BID, _Tick_, _engine_

def _hedging_():
    engine = _engine_()
    engine._netting_ = False
    engine._needs_conversion_ = False
    return engine

def _open_(engine, direction, volume, ask=ASK, bid=BID, minutes=0, stop=None):
    engine._tick_ = _Tick_(ask, bid, datetime(2024, 1, 1, 12, 0) + timedelta(minutes=minutes))
    builder = OpenBuyPositionActionAPI if direction == Direction.Buy else OpenSellPositionActionAPI
    engine._emit_open_(builder(PositionType=PositionType.Normal, Volume=volume, StopLoss=stop, TakeProfit=None), direction)
    return next(reversed(engine._positions_))

def _trades_(engine):
    return [item for item in engine._arg_queue_ if isinstance(item, TradeAPI)]

def test_hedging_holds_several_positions_on_each_side():
    engine = _hedging_()
    for direction, volume in ((Direction.Buy, 1000.0), (Direction.Buy, 2000.0), (Direction.Sell, 3000.0), (Direction.Sell, 1000.0)): _open_(engine, direction, volume)
    sides = [position.Direction for position in engine._positions_.values()]
    assert len(engine._positions_) == 4 and sides.count(Direction.Buy) == 2 and sides.count(Direction.Sell) == 2
    assert not _trades_(engine)

def test_each_position_keeps_its_own_entry_and_costs():
    engine = _hedging_()
    first = _open_(engine, Direction.Buy, 1000.0, ask=1.10000, bid=1.09998)
    second = _open_(engine, Direction.Buy, 3000.0, ask=1.20000, bid=1.19998, minutes=5)
    one, two = engine._positions_[first], engine._positions_[second]
    assert (one.EntryPrice.Price, two.EntryPrice.Price) == (1.10000, 1.20000)
    assert two.CommissionPnL.PnL == pytest.approx(3.0 * one.CommissionPnL.PnL, rel=0.2)
    assert one.SpreadPnL.PnL == pytest.approx(-0.00002 * 1000.0 / 1.10000) and two.SpreadPnL.PnL == pytest.approx(-0.00002 * 3000.0 / 1.20000)

def test_closing_one_position_leaves_the_others_untouched():
    engine = _hedging_()
    first = _open_(engine, Direction.Buy, 1000.0)
    second = _open_(engine, Direction.Buy, 2000.0, minutes=1)
    hedge = _open_(engine, Direction.Sell, 2000.0, minutes=2)
    before = {uid: (position.Volume, position.EntryPrice.Price, position.CommissionPnL.PnL) for uid, position in engine._positions_.items() if uid != first}
    engine._tick_ = _Tick_(1.10102, 1.10100, datetime(2024, 1, 1, 13, 0))
    engine._emit_close_(engine._positions_[first], engine._tick_, UpdateID.ClosedBuyPosition)
    assert set(engine._positions_) == {second, hedge}
    assert {uid: (position.Volume, position.EntryPrice.Price, position.CommissionPnL.PnL) for uid, position in engine._positions_.items()} == before
    trade = _trades_(engine)[-1]
    assert trade.Position.UID == first if hasattr(trade.Position, "UID") else trade.Position == first
    assert trade.GrossPnL.PnL == pytest.approx((1.10100 - ASK) * 1000.0 / 1.10102)

def test_stop_losses_fire_for_each_position_alone():
    engine = _hedging_()
    tight = _open_(engine, Direction.Buy, 1000.0, stop=10.0)
    wide = _open_(engine, Direction.Buy, 1000.0, stop=50.0)
    short = _open_(engine, Direction.Sell, 1000.0, stop=10.0)
    ask, bid = 1.09902, 1.09900
    hits = {uid: engine._stop_level_(position, ask, bid) for uid, position in engine._positions_.items()}
    assert hits[tight][1] == UpdateID.StopLossBuyPosition and hits[wide] == (None, None) and hits[short] == (None, None)
    level, update = hits[tight]
    engine._fill_stop_(engine._positions_[tight], datetime(2024, 1, 1, 12, 30), level, ask, bid, ask, bid, ask - bid, update)
    assert set(engine._positions_) == {wide, short} and _trades_(engine)[-1].ExitPrice.Price == bid

def test_opposite_positions_lock_the_pnl_to_the_spread():
    engine = _hedging_()
    _open_(engine, Direction.Buy, 5000.0)
    _open_(engine, Direction.Sell, 5000.0)
    engine._tick_ = _Tick_(1.12002, 1.12000, datetime(2024, 1, 2, 12, 0))
    for uid in list(engine._positions_): engine._emit_close_(engine._positions_[uid], engine._tick_, UpdateID.ClosedBuyPosition)
    gross = sum(trade.GrossPnL.PnL for trade in _trades_(engine))
    assert gross == pytest.approx(-(ASK - BID) * 5000.0 / 1.12002 - (1.12002 - 1.12000) * 5000.0 / 1.12002, abs=1e-6)