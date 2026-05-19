from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from Library.Parameters import ParametersAPI
from Library.Protocol.Action import ActionID
from Library.Strategy.Rule.Download import DownloadStrategyAPI
from Library.System.Realtime import RealtimeSystemAPI

def _make_system_(market: tuple = (100, 60.0), portfolio: tuple = (100, 60.0), port: int = 5556, **kwargs) -> RealtimeSystemAPI:
    p = ParametersAPI()
    system = RealtimeSystemAPI(
        strategy=DownloadStrategyAPI,
        security=MagicMock(),
        timeframe=MagicMock(),
        parameters=p,
        iid="12345",
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

def test_buffer_thresholds_stored():
    system = _make_system_(market=(42, 1.5), portfolio=(7, 0.5))
    assert system.buffer._market_batch_ == 42
    assert system.buffer._market_interval_ == 1.5
    assert system.buffer._portfolio_batch_ == 7
    assert system.buffer._portfolio_interval_ == 0.5

def test_live_mode_active_both():
    system = _make_system_(market=(100, 60.0), portfolio=(100, 60.0))
    assert system.buffer.ActiveMarket is True
    assert system.buffer.ActivePortfolio is True
    assert system.buffer.Active is True

def test_simulation_mode_active_market_only():
    system = _make_system_(market=(5000, 0.0), portfolio=(0, 0.0))
    assert system.buffer.ActiveMarket is True
    assert system.buffer.ActivePortfolio is False
    assert system.buffer.Active is True

def test_testing_mode_inactive():
    system = _make_system_(market=(0, 0.0), portfolio=(0, 0.0))
    assert system.buffer.ActiveMarket is False
    assert system.buffer.ActivePortfolio is False
    assert system.buffer.Active is False

def test_inactive_methods_are_noops_zero_overhead():
    system = _make_system_(market=(0, 0.0), portfolio=(0, 0.0))
    assert system.buffer.tick is system.buffer._noop_
    assert system.buffer.bar is system.buffer._noop_
    assert system.buffer.order is system.buffer._noop_
    assert system.buffer.position is system.buffer._noop_
    assert system.buffer.trade is system.buffer._noop_

def test_simulation_market_methods_real_portfolio_noop():
    system = _make_system_(market=(100, 0.0), portfolio=(0, 0.0))
    assert system.buffer.tick is not system.buffer._noop_
    assert system.buffer.bar is not system.buffer._noop_
    assert system.buffer.order is system.buffer._noop_
    assert system.buffer.position is system.buffer._noop_
    assert system.buffer.trade is system.buffer._noop_

def test_buffer_starts_empty(realtime_system):
    assert realtime_system.buffer.Empty is True
    assert realtime_system.buffer._tick_buffer_ == []
    assert realtime_system.buffer._bar_buffer_ == []
    assert realtime_system.buffer._order_buffer_ == []
    assert realtime_system.buffer._position_buffer_ == []
    assert realtime_system.buffer._trade_buffer_ == []

def test_empty_false_when_market_batch_reached():
    system = _make_system_(market=(3, 0.0), portfolio=(0, 0.0))
    system.buffer.tick(MagicMock())
    system.buffer.tick(MagicMock())
    system.buffer.tick(MagicMock())
    assert system.buffer.EmptyMarket is False
    assert system.buffer.Empty is False

def test_empty_false_when_portfolio_batch_reached():
    system = _make_system_(market=(0, 0.0), portfolio=(3, 0.0))
    system.buffer.order(MagicMock())
    system.buffer.position(MagicMock())
    system.buffer.trade(MagicMock())
    assert system.buffer.EmptyPortfolio is False
    assert system.buffer.Empty is False

def test_empty_false_when_market_interval_elapsed():
    system = _make_system_(market=(100, 0.001), portfolio=(0, 0.0))
    system.buffer._last_market_flush_ = datetime.now() - timedelta(seconds=1)
    system.buffer.tick(MagicMock())
    assert system.buffer.EmptyMarket is False

def test_buffer_methods_noop_when_inactive():
    system = _make_system_(market=(0, 0.0), portfolio=(0, 0.0))
    system.buffer.tick(MagicMock())
    system.buffer.bar(MagicMock())
    system.buffer.order(MagicMock())
    system.buffer.position(MagicMock())
    system.buffer.trade(MagicMock())
    assert system.buffer._tick_buffer_ == []
    assert system.buffer._bar_buffer_ == []
    assert system.buffer._order_buffer_ == []
    assert system.buffer._position_buffer_ == []
    assert system.buffer._trade_buffer_ == []

def test_simulation_mode_drops_portfolio_records():
    system = _make_system_(market=(100, 60.0), portfolio=(0, 0.0))
    system.buffer.tick(MagicMock())
    system.buffer.order(MagicMock())
    system.buffer.position(MagicMock())
    system.buffer.trade(MagicMock())
    assert len(system.buffer._tick_buffer_) == 1
    assert system.buffer._order_buffer_ == []
    assert system.buffer._position_buffer_ == []
    assert system.buffer._trade_buffer_ == []

def test_receive_update_target_buffers_tick(realtime_system):
    realtime_system.receive_update_target = MagicMock(return_value="tick")
    realtime_system._receive_update_target_()
    assert realtime_system.buffer._tick_buffer_ == ["tick"]

def test_receive_update_bar_buffers_bar_and_five_subticks(realtime_system):
    bar = MagicMock()
    bar.GapTick = "gap"
    bar.OpenTick = "open"
    bar.HighTick = "high"
    bar.LowTick = "low"
    bar.CloseTick = "close"
    realtime_system.receive_update_bar = MagicMock(return_value=bar)
    realtime_system._receive_update_bar_()
    assert realtime_system.buffer._tick_buffer_ == ["gap", "open", "high", "low", "close"]
    assert realtime_system.buffer._bar_buffer_ == [bar]

def test_receive_update_order_buffers_order(realtime_system):
    realtime_system.receive_update_order = MagicMock(return_value="order")
    realtime_system._receive_update_order_()
    assert realtime_system.buffer._order_buffer_ == ["order"]

def test_receive_update_position_buffers_position(realtime_system):
    realtime_system.receive_update_position = MagicMock(return_value="pos")
    realtime_system._receive_update_position_()
    assert realtime_system.buffer._position_buffer_ == ["pos"]

def test_receive_update_trade_buffers_trade(realtime_system):
    realtime_system.receive_update_trade = MagicMock(return_value="trade")
    realtime_system._receive_update_trade_()
    assert realtime_system.buffer._trade_buffer_ == ["trade"]

def test_flush_enqueues_into_per_kind_queues(realtime_system):
    realtime_system.buffer.tick("t")
    realtime_system.buffer.bar("b")
    realtime_system.buffer.order("o")
    realtime_system.buffer.position("p")
    realtime_system.buffer.trade("x")
    realtime_system.buffer.flush()
    assert realtime_system.buffer._tick_queue_.get_nowait() == ["t"]
    assert realtime_system.buffer._bar_queue_.get_nowait() == ["b"]
    assert realtime_system.buffer._order_queue_.get_nowait() == ["o"]
    assert realtime_system.buffer._position_queue_.get_nowait() == ["p"]
    assert realtime_system.buffer._trade_queue_.get_nowait() == ["x"]

def test_flush_clears_buffers(realtime_system):
    realtime_system.buffer.order(MagicMock())
    realtime_system.buffer.flush()
    assert realtime_system.buffer._order_buffer_ == []

def test_flush_signals_worker(realtime_system):
    realtime_system.buffer.order(MagicMock())
    realtime_system.buffer.flush()
    assert realtime_system.buffer._signal_.get_nowait() is True

def test_flush_does_not_signal_when_nothing_pushed(realtime_system):
    realtime_system.buffer.flush()
    assert realtime_system.buffer._signal_.empty()

def test_consume_dispatches_to_market_and_portfolio_push():
    from Library.System import Buffer
    market_mock = MagicMock()
    portfolio_mock = MagicMock()
    saved_market = Buffer.MarketAPI
    saved_portfolio = Buffer.PortfolioAPI
    Buffer.MarketAPI = market_mock
    Buffer.PortfolioAPI = portfolio_mock
    try:
        system = _make_system_()
        db = MagicMock()
        rec = MagicMock()
        rec.dict.return_value = {"k": "v"}
        system.buffer._tick_queue_.put([rec])
        system.buffer._bar_queue_.put([rec])
        system.buffer._order_queue_.put([rec])
        system.buffer._position_queue_.put([rec])
        system.buffer._trade_queue_.put([rec])
        system.buffer._consume_(db)
        market_mock.push_ticks.assert_called_once()
        market_mock.push_bars.assert_called_once()
        portfolio_mock.push_orders.assert_called_once()
        portfolio_mock.push_positions.assert_called_once()
        portfolio_mock.push_trades.assert_called_once()
    finally:
        Buffer.MarketAPI = saved_market
        Buffer.PortfolioAPI = saved_portfolio

def test_consume_drains_all_queues(realtime_system):
    realtime_system.buffer._tick_queue_.put([])
    realtime_system.buffer._bar_queue_.put([])
    realtime_system.buffer._order_queue_.put([])
    realtime_system.buffer._consume_(MagicMock())
    assert realtime_system.buffer._tick_queue_.empty()
    assert realtime_system.buffer._bar_queue_.empty()
    assert realtime_system.buffer._order_queue_.empty()

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
