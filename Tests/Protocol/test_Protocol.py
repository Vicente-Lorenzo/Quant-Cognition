import json
from Library.Protocol.Action import *
from Library.Protocol.Update import *
from Library.Portfolio.Position import PositionType

def test_action_api_serialization():
    action = OpenBuyPositionActionAPI(PositionType=PositionType.Normal, Volume=1000.0, StopLoss=1.0500, TakeProfit=1.0600)
    assert action.ActionID == ActionID.OpenBuyPosition
    assert action.PositionType == PositionType.Normal
    assert action.Volume == 1000.0

    serialized = action.serialize()
    data = json.loads(serialized)
    assert data["ActionID"] == 1
    assert data["PositionType"] == PositionType.Normal.name
    assert data["Volume"] == 1000.0
    assert data["StopLoss"] == 1.0500
    assert data["TakeProfit"] == 1.0600

def test_action_api_helpers():
    a1 = CompleteActionAPI()
    assert a1.ActionID == ActionID.Complete

    a2 = ModifyBuyPositionVolumeActionAPI(PositionID=100, Volume=500.0)
    assert a2.ActionID == ActionID.ModifyBuyPositionVolume
    assert a2.PositionID == 100
    assert a2.Volume == 500.0

def test_update_api():
    update = TickUpdateAPI(Account=None, Market=None, Technical=None, Fundamental=None, Sentimental=None, Portfolio=None, Tick=None)
    assert update.Tick is None
    assert update.Account is None
