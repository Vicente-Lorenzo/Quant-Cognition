import json

from Library.Portfolio.Position import PositionType
from Library.Protocol.Action import *
from Library.Protocol.Update import *

def test_action_id_enum_values():
    assert ActionID.Complete.value == 0
    assert ActionID.OpenBuyPosition.value == 1
    assert ActionID.OpenBuyStopOrder.value == 15
    assert ActionID.OpenBuyLimitOrder.value == 27
    assert ActionID.OpenBuyStopLimitOrder.value == 39

def test_update_id_enum_values():
    assert UpdateID.Complete.value == 0
    assert UpdateID.OpenedBuyPosition.value == 3
    assert UpdateID.BarClosed.value == 13
    assert UpdateID.OpenedBuyStopOrder.value == 19
    assert UpdateID.StopLossBuyPosition.value == 69
    assert UpdateID.Denied.value == 75
    assert UpdateID.Exception.value == 76

def test_open_buy_position_action_serialization():
    action = OpenBuyPositionActionAPI(PositionType=PositionType.Normal, Volume=1000.0, StopLoss=1.0500, TakeProfit=1.0600)
    assert action.ActionID == ActionID.OpenBuyPosition
    data = json.loads(action.serialize())
    assert data["ActionID"] == 1
    assert data["PositionType"] == PositionType.Normal.name
    assert data["Volume"] == 1000.0
    assert data["StopLoss"] == 1.0500
    assert data["TakeProfit"] == 1.0600

def test_open_buy_stop_order_action_serialization():
    action = OpenBuyStopOrderActionAPI(Volume=500.0, StopPrice=1.10, StopLoss=1.09, TakeProfit=1.15)
    data = json.loads(action.serialize())
    assert data["ActionID"] == 15
    assert data["Volume"] == 500.0
    assert data["StopPrice"] == 1.10

def test_open_buy_stop_limit_order_action_serialization():
    action = OpenBuyStopLimitOrderActionAPI(Volume=500.0, StopPrice=1.10, LimitPrice=1.105, StopLoss=1.09, TakeProfit=1.15)
    data = json.loads(action.serialize())
    assert data["ActionID"] == 39
    assert data["StopPrice"] == 1.10
    assert data["LimitPrice"] == 1.105

def test_modify_action_only_carries_relevant_field():
    a = ModifyBuyPositionStopLossActionAPI(PositionID=42, StopLoss=1.0400)
    data = json.loads(a.serialize())
    assert "TakeProfit" not in data
    assert data["PositionID"] == 42
    assert data["StopLoss"] == 1.04

def test_close_action_minimal_payload():
    a = CloseBuyPositionActionAPI(PositionID=99)
    data = json.loads(a.serialize())
    assert data["ActionID"] == 9
    assert data["PositionID"] == 99
    assert len(data) == 2

def test_complete_action_no_fields():
    a = CompleteActionAPI()
    data = json.loads(a.serialize())
    assert data == {"ActionID": 0}

def test_target_action_with_none_clears_target():
    a = BidAboveTargetActionAPI(Bid=None)
    data = json.loads(a.serialize())
    assert data == {"ActionID": 13}

def test_update_construction_with_security_field():
    update = TickUpdateAPI(Account=None, Security=None, Market=None, Technical=None, Fundamental=None, Sentimental=None, Portfolio=None, Tick=None)
    assert update.Tick is None
    assert update.Security is None
    assert update.Account is None

def test_complete_update_construction():
    update = CompleteUpdateAPI(Account=None, Security=None, Market=None, Technical=None, Fundamental=None, Sentimental=None, Portfolio=None)
    assert update.Account is None
    assert update.Security is None

def test_filled_order_carries_order_and_position():
    update = FilledBuyStopOrderUpdateAPI(Account=None, Security=None, Market=None, Technical=None, Fundamental=None, Sentimental=None, Portfolio=None, Bar=None, Order=None, Position=None)
    assert hasattr(update, "Order")
    assert hasattr(update, "Position")

def test_denied_update_fields():
    update = DeniedUpdateAPI(Account=None, Security=None, Market=None, Technical=None, Fundamental=None, Sentimental=None, Portfolio=None, ActionID=ActionID.OpenBuyPosition, Reason="margin")
    assert update.ActionID == ActionID.OpenBuyPosition
    assert update.Reason == "margin"

def test_exception_update_fields():
    update = ExceptionUpdateAPI(Account=None, Security=None, Market=None, Technical=None, Fundamental=None, Sentimental=None, Portfolio=None, Reason="disconnect")
    assert update.Reason == "disconnect"

def test_position_close_carries_trade():
    update = StopLossBuyPositionUpdateAPI(Account=None, Security=None, Market=None, Technical=None, Fundamental=None, Sentimental=None, Portfolio=None, Bar=None, Position=None, Trade=None)
    assert hasattr(update, "Trade")
