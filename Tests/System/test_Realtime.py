from unittest.mock import MagicMock

import pytest

from Library.Utility.Parameter import Parameter
from Library.Portfolio.Account import AccountAPI
from Library.Portfolio.Order import OrderAPI
from Library.Portfolio.Position import PositionAPI
from Library.Portfolio.Trade import TradeAPI
from Library.Protocol.Action import ActionID
from Library.Protocol.Binary import BinaryAPI
from Library.Strategy.Strategy import StrategyAPI
from Library.System.Realtime import RealtimeAPI
from Library.System.System import SystemType

class _Stub_(StrategyAPI):

    def risk_management(self) -> None:
        return None

    def signal_management(self) -> None:
        return None

def _make_system_(system: SystemType = SystemType.Live, database: str = "Quant", **kwargs) -> RealtimeAPI:
    p = Parameter({}, "test.yml")
    system = RealtimeAPI(
        system=system,
        strategy=_Stub_,
        security=MagicMock(),
        timeframe=MagicMock(),
        parameters=p,
        iid="12345",
        database=database,
        **kwargs
    )
    system._transport_ = MagicMock()
    system._db_ = MagicMock()
    return system

@pytest.fixture
def realtime_system():
    return _make_system_()

def test_receive_update_id_reads_one_record(realtime_system):
    from Library.Protocol.Update import UpdateID
    record = bytes([UpdateID.Tick.value, 1, 2, 3])
    realtime_system._receive_ = MagicMock(side_effect=[record, bytes([UpdateID.Complete.value])])
    assert realtime_system.receive_update_id() == UpdateID.Tick
    assert realtime_system._last_update_data_ == record
    assert realtime_system.receive_update_id() == UpdateID.Complete
    assert realtime_system._receive_.call_count == 2

def test_realtime_system_initialization(realtime_system):
    assert realtime_system._iid_ == "12345"

def test_realtime_system_management_initial_state(realtime_system):
    engine = realtime_system.system_management()
    assert engine.At.Name == "Initialization"

def test_realtime_system_management_has_three_states(realtime_system):
    engine = realtime_system.system_management()
    names = {s for s in engine._states_}
    assert names == {"Initialization", "Execution", "Termination"}

def test_direct_attribute_state(realtime_system):
    assert realtime_system.account is None
    assert realtime_system.security is realtime_system._security_
    assert realtime_system.market is None
    assert realtime_system.technical is None
    assert realtime_system.fundamental is None
    assert realtime_system.sentimental is None
    assert realtime_system.portfolio is None

def test_a_cbot_run_keeps_no_write_buffer(realtime_system):
    assert not hasattr(realtime_system, "_portfolio_") and not hasattr(realtime_system, "_universe_") and not hasattr(realtime_system, "_session_")

def test_market_updates_are_never_stored(realtime_system):
    tick, bar = MagicMock(), MagicMock()
    realtime_system.receive_update_tick = MagicMock(return_value=tick)
    realtime_system.receive_update_bar = MagicMock(return_value=bar)
    assert realtime_system._receive_update_tick_() is tick and realtime_system._receive_update_bar_() is bar
    assert not hasattr(realtime_system, "_market_")

def test_portfolio_updates_pass_through_without_being_stored(realtime_system):
    order, position, trade, account, security = MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock()
    realtime_system.receive_update_order = MagicMock(return_value=order)
    realtime_system.receive_update_position = MagicMock(return_value=position)
    realtime_system.receive_update_trade = MagicMock(return_value=trade)
    realtime_system.receive_update_account = MagicMock(return_value=account)
    realtime_system.receive_update_security = MagicMock(return_value=security)
    assert realtime_system._receive_update_order_() is order and realtime_system._receive_update_position_() is position and realtime_system._receive_update_trade_() is trade
    assert realtime_system._receive_update_account_() is account and realtime_system._receive_update_security_() is security
    account.save.assert_not_called()
    security.save.assert_not_called()

def test_warmup_leaves_buffering_to_the_bar_receiver(realtime_system):
    realtime_system._db_ = None
    realtime_system._indicator_window_ = lambda: 999
    bar = MagicMock()
    update = MagicMock(); update.Bar = bar
    engine = realtime_system.system_management()
    initialization = engine.state(name="Initialization")
    transition = next(t for t in initialization._transitions_ if t is not None and getattr(t, "Action", None) and t.Action.__name__ == "warmup")
    transition.perform(update)
    assert realtime_system._sync_buffer_ == [bar]

def test_warmup_reuses_the_database_frame_at_execution(realtime_system, monkeypatch):
    from datetime import datetime, timedelta
    from Library.Database.Dataframe import pl
    from Library.Market.Market import MarketAPI
    stamps = [datetime(2024, 1, 1) + timedelta(hours=hour) for hour in range(3)]
    pulls = []
    monkeypatch.setattr(MarketAPI, "pull_bars", staticmethod(lambda *args, **kwargs: (pulls.append(kwargs), pl.DataFrame({"Timestamp": stamps[:2]}))[1]))
    realtime_system._indicator_window_ = lambda: 2
    realtime_system._security_.UID = 1
    realtime_system._timeframe_.Seconds = 3600
    bar = MagicMock()
    bar.Timestamp.DateTime = stamps[2]
    bar.dict.return_value = {"Timestamp": stamps[2]}
    engine = realtime_system.system_management()
    initialization = engine.state(name="Initialization")
    warmup = next(t for t in initialization._transitions_ if t is not None and getattr(t, "Action", None) and t.Action.__name__ == "warmup")
    execute = next(t for t in initialization._transitions_ if t is not None and getattr(t, "Action", None) and t.Action.__name__ == "execute")
    warmup.perform(MagicMock(Bar=bar))
    update = MagicMock()
    execute.perform(update)
    assert len(pulls) == 1
    assert update.Market.init_data.call_args.args[0]["Timestamp"].to_list() == stamps

def test_warmup_emits_execution_when_window_reached(realtime_system):
    realtime_system._db_ = None
    realtime_system._indicator_window_ = lambda: 1
    bar = MagicMock()
    update = MagicMock(); update.Bar = bar
    engine = realtime_system.system_management()
    initialization = engine.state(name="Initialization")
    transition = next(t for t in initialization._transitions_ if t is not None and getattr(t, "Action", None) and t.Action.__name__ == "warmup")
    actions = transition.perform(update)
    assert realtime_system._warmup_ready_ is True
    assert actions[0].ActionID == ActionID.Execution

def test_init_market_clears_sync_buffer(realtime_system):
    bar = MagicMock()
    bar.Timestamp.DateTime = "ts"
    bar.dict.return_value = {}
    realtime_system._sync_buffer_.append(bar)
    update = MagicMock()
    update.Portfolio.Account = MagicMock()
    engine = realtime_system.system_management()
    initialization = engine.state(name="Initialization")
    transition = next(t for t in initialization._transitions_ if t is not None and getattr(t, "Action", None) and t.Action.__name__ == "execute")
    transition.perform(update)
    assert realtime_system._sync_buffer_ == []

def test_send_serializes_to_transport(realtime_system):
    from Library.Protocol.Action import CompleteActionAPI
    realtime_system.send_action(CompleteActionAPI())
    realtime_system._transport_.send.assert_called_once()
    sent_payload = realtime_system._transport_.send.call_args[0][0]
    assert isinstance(sent_payload, bytes)
    assert sent_payload[0] == ActionID.Complete.value

def test_receive_update_denied_returns_action_id_and_reason(realtime_system):
    denied_codec = BinaryAPI('B', 'B', 's')
    realtime_system._last_update_data_ = denied_codec.pack(77, ActionID.OpenBuyPosition.value, "no margin")
    action_id, reason = realtime_system.receive_update_denied()
    assert action_id == ActionID.OpenBuyPosition
    assert reason == "no margin"

def test_receive_update_exception_returns_reason(realtime_system):
    exception_codec = BinaryAPI('B', 's')
    realtime_system._last_update_data_ = exception_codec.pack(78, "disconnect")
    assert realtime_system.receive_update_exception() == "disconnect"

def _security_payload_(extra_day: int = 3, trading_mode: int = 0) -> bytes:
    return b'\x00' + RealtimeAPI._binary_security_.pack(1, "EUR", "USD", "Euro vs US Dollar", 5, 0.00001, 0.0001, 100000, 1000.0, 10000000.0, 1000.0, 1, 30.0, 0, -1.5, -1.2, extra_day, trading_mode)

def _stored_security_():
    from Library.Universe.Contract import ContractAPI
    from Library.Universe.Security import SecurityAPI
    from Library.Universe.Ticker import ContractType
    return SecurityAPI(Ticker="EURUSD", Provider="Spotware(cTrader)", Type=ContractType.Spot, Contract=ContractAPI(UID=1))

def test_receive_update_security_updates_and_returns_security(realtime_system):
    from Library.Universe.Contract import CommissionMode, SwapMode, TradingMode
    from Library.Utility.Datetime import Weekday
    realtime_system._security_ = _stored_security_()
    realtime_system._last_update_data_ = _security_payload_()
    sec = realtime_system.receive_update_security()
    assert sec is realtime_system._security_ and sec.Symbol == 1
    assert (sec.Ticker.BaseAsset, sec.Ticker.QuoteAsset, sec.Ticker.Description) == ("EUR", "USD", "Euro vs US Dollar")
    assert (sec.Contract.Digits, sec.Contract.PointSize, sec.Contract.PipSize, sec.Contract.LotSize) == (5, 0.00001, 0.0001, 100000)
    assert (sec.Contract.VolumeMin, sec.Contract.VolumeMax, sec.Contract.VolumeStep) == (1000.0, 10000000.0, 1000.0)
    assert (sec.Contract.CommissionMode, sec.Contract.Commission) == (CommissionMode.BaseAssetPerOneLot, 30.0)
    assert (sec.Contract.SwapMode, sec.Contract.SwapLong, sec.Contract.SwapShort, sec.Contract.SwapExtraDay) == (SwapMode.Pips, -1.5, -1.2, Weekday.Wednesday)
    assert sec.Contract.TradingMode == TradingMode.Enabled and sec.Contract.UpdatedBy == "Connector"

def test_a_security_update_reads_ctraders_own_trading_modes_and_a_missing_triple_swap_day(realtime_system):
    from Library.Universe.Contract import TradingMode
    expected = {0: TradingMode.Enabled, 1: TradingMode.CloseOnlyMode, 2: TradingMode.DisabledWithPendingsExecution, 3: TradingMode.DisabledWithoutPendingsExecution}
    for mode, trading in expected.items():
        realtime_system._security_ = _stored_security_()
        realtime_system._last_update_data_ = _security_payload_(extra_day=-1, trading_mode=mode)
        contract = realtime_system.receive_update_security().Contract
        assert contract.TradingMode == trading and contract.SwapExtraDay is None

def test_a_security_without_stored_terms_takes_the_ones_the_connector_sends(realtime_system):
    security = _stored_security_()
    security._contract_ = None
    realtime_system._security_ = security
    realtime_system._last_update_data_ = _security_payload_()
    contract = realtime_system.receive_update_security().Contract
    assert contract is not None and contract.Digits == 5 and contract._owner_ is security

def test_exit_closes_the_stack():
    system = _make_system_()
    calls = []
    system._connected_ = True
    system._stack_ = MagicMock()
    system._stack_.__exit__ = MagicMock(side_effect=lambda *a, **k: calls.append("stack_exit"))
    system.__exit__(None, None, None)
    assert calls == ["stack_exit"] and system._connected_ is False

def test_a_wire_contract_is_recorded_with_its_own_provenance(tmp_path):
    from datetime import datetime
    from types import SimpleNamespace
    from Library.Universe.Contract import ContractAPI
    from Library.Universe.Security import SecurityAPI
    from Library.Universe.Ticker import ContractType
    from Library.Utility.IO import read_yaml
    system = _make_system_(run=str(tmp_path))
    stored = SecurityAPI(Ticker="EURUSD", Provider="Spotware(cTrader)", Type=ContractType.Spot, Contract=ContractAPI(SwapLong=-2.445, SwapShort=-0.105, UpdatedAt=datetime(2026, 9, 10, 18, 30), UpdatedBy="Autosave")).Contract
    system._security_ = SimpleNamespace(Ticker=None, Contract=stored)
    system._binary_security_ = SimpleNamespace(unpack=lambda data, offset: (1, "EUR", "USD", "Euro vs US Dollar", 5, 0.00001, 0.0001, 100000, 1000.0, 10000000.0, 1000.0, 0, 45.0, 0, -9.0, -1.0, 3, 0))
    system._last_update_data_ = b""
    system.receive_update_security()
    written = read_yaml(tmp_path / "Input" / "Contract.yml", safe=False)
    assert (written["SwapLong"], written["SwapShort"], written["UpdatedBy"]) == (-9.0, -1.0, "Connector")
    assert written["UpdatedAt"] > datetime(2026, 9, 10, 18, 30)

def test_a_wire_bar_carries_both_sides_and_the_mid_of_each_extreme(realtime_system):
    import struct
    from Library.Protocol.Update import UpdateID
    realtime_system._security_ = None
    realtime_system._timeframe_ = None
    ticks = [(1706745600000 + index, 1.1 + index / 1000, 1.0 + index / 1000, 1.0, 1.0, 1.0, 1.0, 1.0) for index in range(9)]
    payload = struct.pack("<Bq", UpdateID.BarClosed.value, 1706745600000) + b"".join(realtime_system._binary_tick_.pack(*tick) for tick in ticks) + struct.pack("<d", 42.0)
    assert len(payload) == realtime_system._bar_payload_ == 593
    realtime_system._last_update_data_ = payload
    bar = realtime_system.receive_update_bar()
    assert (bar.HighPoint.Ask.Price, bar.HighPoint.Bid.Price, bar.LowPoint.Ask.Price, bar.LowPoint.Bid.Price) == (ticks[2][1], ticks[3][2], ticks[5][1], ticks[6][2])
    assert (bar.HighPoint.Mid.Price, bar.LowPoint.Mid.Price) == ((ticks[4][1] + ticks[4][2]) / 2, (ticks[7][1] + ticks[7][2]) / 2)
    assert bar.ClosePoint.AskTick is bar.ClosePoint.BidTick is bar.ClosePoint.MidTick and bar.ClosePoint.Bid.Price == ticks[8][2] and bar.Volume == 42.0
    assert bar.OpenPoint.MidTick is bar.OpenPoint.AskTick and bar.GapPoint.MidTick is bar.GapPoint.BidTick

def test_the_market_prices_at_the_side_its_strategy_declares():
    from Library.Market.Price import PriceMode
    system = _make_system_()
    system._assemble_()
    assert system.market.ClosePoints.Price is system.market.ClosePoints.Bid
    system._strategy_ = type("_Mid_", (_Stub_,), {"Pricing": PriceMode.Mid})
    system._assemble_()
    assert system.market.ClosePoints.Price is system.market.ClosePoints.Mid and system.market.Ticks.Price is system.market.Ticks.Mid