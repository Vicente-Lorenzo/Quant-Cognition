from unittest.mock import MagicMock

import pytest

from Library.Parameter import ParameterAPI
from Library.Portfolio.Account import AccountAPI
from Library.Portfolio.Order import OrderAPI
from Library.Portfolio.Position import PositionAPI
from Library.Portfolio.Trade import TradeAPI
from Library.Protocol.Action import ActionID
from Library.Strategy.Rule.Download import DownloadStrategyAPI
from Library.System.Realtime import RealtimeAPI
from Library.System.System import SystemType
from Library.Market.Tick import TickAPI
from Library.Market.Bar import BarAPI

def _make_system_(market: tuple = (100, 60.0), portfolio: tuple = (100, 60.0), port: int = 5556, system: SystemType = SystemType.Live, database: str = "Quant", **kwargs) -> RealtimeAPI:
    p = ParameterAPI()
    system = RealtimeAPI(
        system=system,
        strategy=DownloadStrategyAPI,
        security=MagicMock(),
        timeframe=MagicMock(),
        parameters=p,
        iid="12345",
        database=database,
        market=market,
        portfolio=portfolio,
        port=port,
        **kwargs
    )
    system._context_ = MagicMock()
    system._socket_ = MagicMock()
    system._db_ = MagicMock()
    return system

@pytest.fixture
def realtime_system():
    return _make_system_()

def test_realtime_system_initialization(realtime_system):
    assert realtime_system._iid_ == "12345"
    assert realtime_system._port_ == 5556

def test_realtime_system_management_initial_state(realtime_system):
    engine = realtime_system.system_management()
    assert engine.At.Name == "Initialisation"

def test_realtime_system_management_has_three_states(realtime_system):
    engine = realtime_system.system_management()
    names = {s for s in engine._states_}
    assert names == {"Initialisation", "Execution", "Termination"}

def test_direct_attribute_state(realtime_system):
    assert realtime_system.account is None
    assert realtime_system.security is realtime_system._security_
    assert realtime_system.market is None
    assert realtime_system.technical is None
    assert realtime_system.fundamental is None
    assert realtime_system.sentimental is None
    assert realtime_system.portfolio is None

def test_buffer_instances_carry_correct_types(realtime_system):
    assert realtime_system._market_._types_ == (TickAPI, BarAPI)
    assert realtime_system._portfolio_._types_ == (AccountAPI, OrderAPI, PositionAPI, TradeAPI)

def test_live_mode_both_buffers_active():
    system = _make_system_(market=(100, 60.0), portfolio=(100, 60.0))
    assert system._market_.Active is True
    assert system._portfolio_.Active is True

def test_simulation_mode_only_market_active():
    system = _make_system_(market=(5000, 0.0), portfolio=(0, 0.0))
    assert system._market_.Active is True
    assert system._portfolio_.Active is False

def test_testing_mode_both_inactive():
    system = _make_system_(market=(0, 0.0), portfolio=(0, 0.0))
    assert system._market_.Active is False
    assert system._portfolio_.Active is False

def test_receive_update_target_routes_to_market_buffer(realtime_system):
    realtime_system._market_.add = MagicMock()
    tick = MagicMock()
    realtime_system.receive_update_target = MagicMock(return_value=tick)
    realtime_system._receive_update_target_()
    realtime_system._market_.add.assert_called_once_with(tick)

def test_receive_update_bar_routes_bar_and_subticks_to__market_(realtime_system):
    realtime_system._market_.add = MagicMock()
    g, o, h, l, c = MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock()
    bar = MagicMock()
    bar.GapTick, bar.OpenTick, bar.HighTick, bar.LowTick, bar.CloseTick = g, o, h, l, c
    realtime_system.receive_update_bar = MagicMock(return_value=bar)
    realtime_system._receive_update_bar_()
    assert [call.args[0] for call in realtime_system._market_.add.call_args_list] == [g, o, h, l, c, bar]

def test_receive_update_order_routes_to_portfolio_buffer(realtime_system):
    realtime_system._portfolio_.add = MagicMock()
    order = MagicMock()
    realtime_system.receive_update_order = MagicMock(return_value=order)
    realtime_system._receive_update_order_()
    realtime_system._portfolio_.add.assert_called_once_with(order)

def test_receive_update_position_routes_to_portfolio_buffer(realtime_system):
    realtime_system._portfolio_.add = MagicMock()
    position = MagicMock()
    realtime_system.receive_update_position = MagicMock(return_value=position)
    realtime_system._receive_update_position_()
    realtime_system._portfolio_.add.assert_called_once_with(position)

def test_receive_update_trade_routes_to_portfolio_buffer(realtime_system):
    realtime_system._portfolio_.add = MagicMock()
    trade = MagicMock()
    realtime_system.receive_update_trade = MagicMock(return_value=trade)
    realtime_system._receive_update_trade_()
    realtime_system._portfolio_.add.assert_called_once_with(trade)

def test_simulation_mode_drops_portfolio_records():
    system = _make_system_(market=(100, 60.0), portfolio=(0, 0.0))
    assert system._portfolio_.add is system._portfolio_._noop_

def test_sync_market_routes_warmup_to_market_buffer(realtime_system):
    realtime_system._market_.add = MagicMock()
    g, o, h, l, c = MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock()
    bar = MagicMock()
    bar.GapTick, bar.OpenTick, bar.HighTick, bar.LowTick, bar.CloseTick = g, o, h, l, c
    update = MagicMock(); update.Bar = bar
    engine = realtime_system.system_management()
    initialisation = engine.state(name="Initialisation")
    transition = next(t for t in initialisation._transitions_ if t is not None and getattr(t, "Action", None) and t.Action.__name__ == "sync_market")
    transition.perform(update)
    assert [call.args[0] for call in realtime_system._market_.add.call_args_list] == [g, o, h, l, c, bar]
    assert realtime_system._sync_buffer_ == [bar]

def test_init_market_clears_sync_buffer(realtime_system):
    bar = MagicMock()
    bar.Timestamp.DateTime = "ts"
    bar.dict.return_value = {}
    realtime_system._sync_buffer_.append(bar)
    update = MagicMock()
    update.Portfolio.Account = MagicMock()
    engine = realtime_system.system_management()
    initialisation = engine.state(name="Initialisation")
    transition = next(t for t in initialisation._transitions_ if t is not None and getattr(t, "Action", None) and t.Action.__name__ == "init_market")
    transition.perform(update)
    assert realtime_system._sync_buffer_ == []

def test_send_action_serializes_to_socket(realtime_system):
    from Library.Protocol.Action import CompleteActionAPI
    realtime_system.send_action(CompleteActionAPI())
    realtime_system._socket_.send_string.assert_called_once()
    sent_payload = realtime_system._socket_.send_string.call_args[0][0]
    assert '"ActionID": 0' in sent_payload

def test_receive_update_denied_returns_action_id_and_reason(realtime_system):
    realtime_system._last_update_msg_ = {"ActionID": ActionID.OpenBuyPosition.value, "Reason": "no margin"}
    action_id, reason = realtime_system.receive_update_denied()
    assert action_id == ActionID.OpenBuyPosition
    assert reason == "no margin"

def test_receive_update_exception_returns_reason(realtime_system):
    realtime_system._last_update_msg_ = {"Reason": "disconnect"}
    assert realtime_system.receive_update_exception() == "disconnect"

def test_receive_update_security_returns_init_security(realtime_system):
    assert realtime_system.receive_update_security() is realtime_system._security_

def test_exit_drains_buffers_before_closing_stack():
    system = _make_system_()
    calls = []
    system._market_._active_ = True
    system._portfolio_._active_ = True
    system._market_.shutdown = lambda: calls.append("market_shutdown")
    system._portfolio_.shutdown = lambda: calls.append("portfolio_shutdown")
    system._stack_ = MagicMock()
    system._stack_.__exit__ = MagicMock(side_effect=lambda *a, **k: calls.append("stack_exit"))
    system.__exit__(None, None, None)
    assert calls.index("market_shutdown") < calls.index("stack_exit")
    assert calls.index("portfolio_shutdown") < calls.index("stack_exit")
