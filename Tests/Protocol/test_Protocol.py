import struct
import math

from Library.Portfolio.Position import PositionType
from Library.Protocol.Action import *
from Library.Protocol.Update import *
from Library.Protocol.Binary import BinaryAPI

def test_action_id_enum_values():
    assert ActionID.Init.value == 0
    assert ActionID.OpenBuyPosition.value == 43
    assert ActionID.OpenBuyStopOrder.value == 5
    assert ActionID.OpenBuyLimitOrder.value == 17
    assert ActionID.OpenBuyStopLimitOrder.value == 29
    assert ActionID.Complete.value == 53

def test_update_id_enum_values():
    assert UpdateID.Init.value == 0
    assert UpdateID.Account.value == 1
    assert UpdateID.Security.value == 2
    assert UpdateID.Tick.value == 3
    assert UpdateID.BarOpened.value == 4
    assert UpdateID.BarClosed.value == 5
    assert UpdateID.OpenedBuyStopOrder.value == 10
    assert UpdateID.OpenedBuyPosition.value == 60
    assert UpdateID.StopLossBuyPosition.value == 70
    assert UpdateID.Complete.value == 76
    assert UpdateID.Denied.value == 77
    assert UpdateID.Exception.value == 78
    assert UpdateID.Shutdown.value == 79

def test_open_buy_position_action_serialization():
    action = OpenBuyPositionActionAPI(PositionType=PositionType.Normal, Volume=1000.0, StopLoss=1.0500, TakeProfit=1.0600)
    assert action.ActionID == ActionID.OpenBuyPosition
    data = action.serialize()
    assert isinstance(data, bytes)
    assert data[0] == ActionID.OpenBuyPosition.value

def test_open_buy_stop_order_action_serialization():
    action = OpenBuyStopOrderActionAPI(Volume=500.0, StopPrice=1.10, StopLoss=1.09, TakeProfit=1.15)
    data = action.serialize()
    assert data[0] == ActionID.OpenBuyStopOrder.value

def test_open_buy_stop_limit_order_action_serialization():
    action = OpenBuyStopLimitOrderActionAPI(Volume=500.0, StopPrice=1.10, LimitPrice=1.105, StopLoss=1.09, TakeProfit=1.15)
    data = action.serialize()
    assert data[0] == ActionID.OpenBuyStopLimitOrder.value

def test_modify_action_only_carries_relevant_field():
    a = ModifyBuyPositionStopLossActionAPI(PositionID=42, StopLoss=1.0400)
    data = a.serialize()
    assert data[0] == ActionID.ModifyBuyPositionStopLoss.value
    _, pid, sl = struct.unpack_from("<Bid", data)
    assert pid == 42
    assert abs(sl - 1.04) < 1e-10

def test_close_action_minimal_payload():
    a = CloseBuyPositionActionAPI(PositionID=99)
    data = a.serialize()
    assert data[0] == ActionID.CloseBuyPosition.value
    pid = struct.unpack_from("<i", data, 1)[0]
    assert pid == 99
    assert len(data) == 5

def test_complete_action_no_fields():
    a = CompleteActionAPI()
    data = a.serialize()
    assert len(data) == 1
    assert data[0] == ActionID.Complete.value

def test_target_action_with_none_clears_target():
    a = BidAboveTargetActionAPI(Bid=None)
    data = a.serialize()
    assert data[0] == ActionID.BidAboveTarget.value
    price = struct.unpack_from("<d", data, 1)[0]
    assert math.isnan(price)

def test_codec_tick_round_trip():
    codec = BinaryAPI('B', 'q', 'd', 'd', 'd', 'd', 'd', 'd', 'd')
    data = codec.pack(UpdateID.Tick.value, 1706745600000, 1.08432, 1.08430, 1.0, 1.0, 1.08432, 1.08430, 100.0)
    _, ts, ask, bid, ab, bb, aq, bq, vol = codec.unpack(data)
    assert ts == 1706745600000
    assert abs(ask - 1.08432) < 1e-10
    assert abs(bid - 1.08430) < 1e-10
    assert vol == 100.0

def test_codec_bar_subtick_round_trip():
    tick_codec = BinaryAPI('q', 'd', 'd', 'd', 'd', 'd', 'd', 'd')
    ts = 1706745600000
    tick_values = (ts, 1.08, 1.07, 1.0, 1.0, 1.08, 1.07, 50.0)
    bar_data = struct.pack('<Bq', UpdateID.BarClosed.value, ts)
    for _ in range(5):
        bar_data += tick_codec.pack(*tick_values)
    bar_data += struct.pack('<d', 1000.0)
    assert len(bar_data) == 337
    bar_ts = struct.unpack_from('<q', bar_data, 1)[0]
    assert bar_ts == ts
    off = 9
    for _ in range(5):
        sub_ts, ask, bid, ab, bb, aq, bq, vol = tick_codec.unpack(bar_data, off)
        assert sub_ts == ts
        assert abs(ask - 1.08) < 1e-10
        off += tick_codec._size_
    volume = struct.unpack_from('<d', bar_data, off)[0]
    assert volume == 1000.0

def test_codec_account_round_trip():
    codec = BinaryAPI('B', 's', 's', 'B', 's', 'd', 'd', 'd', 'd', 'd', 'd', 'd', 'd', 'B')
    data = codec.pack(UpdateID.Account.value, "12345", "Live", 1, "USD", 10000.0, 10500.0, 0.0, 100.0, 500.0, 9500.0, 2100.0, 50.0, 0)
    _, number, env, acct_type, asset, bal, eq, cr, lev, mu, mf, ml, ms_, mm = codec.unpack(data)
    assert number == "12345"
    assert env == "Live"
    assert bal == 10000.0
    assert asset == "USD"

def test_codec_security_round_trip():
    codec = BinaryAPI('B', 's', 's', 'i', 'd', 'd', 'd', 'd', 'd', 'd', 'd', 'B', 'd', 'd', 'B', 'i')
    data = codec.pack(UpdateID.Security.value, "EUR", "USD", 5, 0.00001, 0.0001, 100000.0, 1000.0, 10000000.0, 1000.0, 7.0, 2, -5.0, 3.0, 1, 3)
    _, base, quote, digits, ps, pips, lots, vmin, vmax, vstep, comm, cm, sl, ss, sm, sed = codec.unpack(data)
    assert base == "EUR"
    assert quote == "USD"
    assert digits == 5
    assert abs(pips - 0.0001) < 1e-15
    assert cm == 2
    assert sed == 3

def test_codec_position_round_trip():
    codec = BinaryAPI('B', 'i', 'B', 'B', 'q', 'd', 'd', 'd', 'd', 'd', 'd', 'd', 'd', 'D', 'D', 's')
    data = codec.pack(UpdateID.OpenedBuyPosition.value, 42, 0, 0, 1706745600000, 1.08, 1000.0, 0.01, 50.0, -5.0, -1.0, 44.0, 100.0, 1.07, 1.09, "label")
    _, uid, pos_type, direction, entry_ts, ep, vol, qty, gp, cp, sp, np_, um, sl, tp, label = codec.unpack(data)
    assert uid == 42
    assert pos_type == 0
    assert sl == 1.07
    assert tp == 1.09
    assert label == "label"

def test_codec_position_nullable_fields():
    codec = BinaryAPI('B', 'i', 'B', 'B', 'q', 'd', 'd', 'd', 'd', 'd', 'd', 'd', 'd', 'D', 'D', 's')
    data = codec.pack(UpdateID.OpenedBuyPosition.value, 1, 0, 0, 1706745600000, 1.08, 1000.0, 0.01, 0.0, 0.0, 0.0, 0.0, 0.0, None, None, None)
    _, uid, pos_type, direction, entry_ts, ep, vol, qty, gp, cp, sp, np_, um, sl, tp, label = codec.unpack(data)
    assert sl is None
    assert tp is None
    assert label is None

def test_codec_trade_round_trip():
    codec = BinaryAPI('B', 'i', 'i', 'B', 'B', 'q', 'q', 'd', 'd', 'd', 'd', 'd', 'd', 'd', 'd', 's')
    data = codec.pack(UpdateID.ClosedBuyPosition.value, 99, 42, 0, 0, 1706745600000, 1706745700000, 1.08, 1.09, 1000.0, 0.01, 100.0, -5.0, -1.0, 94.0, "lb")
    _, uid, pos_id, trade_type, direction, ets, xts, ep, xp, vol, qty, gp, cp, sp, np_, label = codec.unpack(data)
    assert uid == 99
    assert pos_id == 42
    assert ep == 1.08
    assert xp == 1.09

def test_codec_order_round_trip():
    codec = BinaryAPI('B', 'i', 'B', 'B', 'd', 'd', 'D', 'D', 'q', 's')
    data = codec.pack(UpdateID.OpenedBuyStopOrder.value, 7, 0, 0, 500.0, 1.10, 1.09, 1.15, 1706745600000, "lb")
    _, uid, otype, direction, vol, target, sl, tp, exp, label = codec.unpack(data)
    assert uid == 7
    assert otype == 0
    assert direction == 0
    assert sl == 1.09
    assert exp == 1706745600000

def test_codec_order_nullable_expiration():
    codec = BinaryAPI('B', 'i', 'B', 'B', 'd', 'd', 'D', 'D', 'q', 's')
    data = codec.pack(UpdateID.OpenedBuyLimitOrder.value, 8, 1, 0, 500.0, 1.10, None, None, 0, None)
    _, uid, otype, direction, vol, target, sl, tp, exp, label = codec.unpack(data)
    assert sl is None
    assert tp is None
    assert label is None

def test_codec_denied_round_trip():
    codec = BinaryAPI('B', 'B', 's')
    data = codec.pack(UpdateID.Denied.value, ActionID.OpenBuyPosition.value, "no margin")
    _, action_id, reason = codec.unpack(data)
    assert action_id == ActionID.OpenBuyPosition.value
    assert reason == "no margin"

def test_codec_exception_round_trip():
    codec = BinaryAPI('B', 's')
    data = codec.pack(UpdateID.Exception.value, "disconnect")
    _, reason = codec.unpack(data)
    assert reason == "disconnect"

def test_codec_init_round_trip():
    codec = BinaryAPI('B', 'i')
    data = codec.pack(UpdateID.Init.value, 1234)
    assert data[0] == UpdateID.Init.value
    _, pid = codec.unpack(data)
    assert pid == 1234

def test_codec_field_count_validation():
    codec = BinaryAPI('B', 'i', 'd')
    try:
        codec.pack(1, 2)
        assert False
    except ValueError:
        pass

def test_codec_fixed_size():
    tick = BinaryAPI('q', 'd', 'd', 'd', 'd', 'd', 'd', 'd')
    assert tick._size_ == 64
    single = BinaryAPI('B')
    assert single._size_ == 1
    with_str = BinaryAPI('i', 's', 'd')
    assert with_str._size_ is None

def test_update_construction_with_security_field():
    update = TickUpdateAPI(Account=None, Security=None, Market=None, Technical=None, Fundamental=None, Sentimental=None, Portfolio=None, Tick=None)
    assert update.Tick is None
    assert update.Security is None
    assert update.Account is None

def test_complete_update_construction():
    update = CompleteUpdateAPI(Account=None, Security=None, Market=None, Technical=None, Fundamental=None, Sentimental=None, Portfolio=None)
    assert update.Account is None
    assert update.Security is None

def test_filled_order_carries_order():
    update = FilledBuyStopOrderUpdateAPI(Account=None, Security=None, Market=None, Technical=None, Fundamental=None, Sentimental=None, Portfolio=None, Order=None)
    assert hasattr(update, "Order")

def test_denied_update_fields():
    update = DeniedUpdateAPI(Account=None, Security=None, Market=None, Technical=None, Fundamental=None, Sentimental=None, Portfolio=None, ActionID=ActionID.OpenBuyPosition, Reason="margin")
    assert update.ActionID == ActionID.OpenBuyPosition
    assert update.Reason == "margin"

def test_exception_update_fields():
    update = ExceptionUpdateAPI(Account=None, Security=None, Market=None, Technical=None, Fundamental=None, Sentimental=None, Portfolio=None, Reason="disconnect")
    assert update.Reason == "disconnect"

def test_position_close_carries_trade():
    update = StopLossBuyPositionUpdateAPI(Account=None, Security=None, Market=None, Technical=None, Fundamental=None, Sentimental=None, Portfolio=None, Position=None, Trade=None)
    assert hasattr(update, "Trade")
