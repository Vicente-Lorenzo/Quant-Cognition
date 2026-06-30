from types import SimpleNamespace

from Library.Strategy.Model.Action import ActionAPI, SizingMode

def _update_(close=1.15, balance=10000.0):
    contract = SimpleNamespace(VolumeStep=1000.0, VolumeMin=1000.0, VolumeMax=100000.0)
    portfolio = SimpleNamespace(Account=SimpleNamespace(Balance=balance), Security=SimpleNamespace(Contract=contract))
    bar = SimpleNamespace(CloseTick=SimpleNamespace(Bid=SimpleNamespace(Price=close)))
    return SimpleNamespace(Bar=bar, Portfolio=portfolio)

def test_fixed_maximum_floors_to_step():
    action = ActionAPI(mode=SizingMode.Fixed, maximum=12345.0)
    assert action.maximum_volume(_update_()) == 12000.0

def test_percentage_maximum_of_account():
    action = ActionAPI(mode=SizingMode.Percentage, maximum=50.0)
    assert action.maximum_volume(_update_(close=1.15, balance=10000.0)) == 4000.0

def test_target_signs_and_floors():
    action = ActionAPI(mode=SizingMode.Fixed, maximum=10000.0)
    assert action.target(0.5, _update_()) == 5000.0
    assert action.target(-0.5, _update_()) == -5000.0

def test_target_below_minimum_is_flat():
    action = ActionAPI(mode=SizingMode.Fixed, maximum=10000.0)
    assert action.target(0.05, _update_()) == 0.0

def test_deadzone_suppresses_small_actions():
    action = ActionAPI(mode=SizingMode.Fixed, maximum=10000.0, deadzone=0.2)
    assert action.target(0.1, _update_()) == 0.0
    assert action.target(0.5, _update_()) == 5000.0