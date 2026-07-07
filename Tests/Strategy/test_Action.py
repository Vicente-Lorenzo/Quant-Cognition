from types import SimpleNamespace

from Library.Portfolio.Sizing import SizingMode
from Library.Strategy.Model.Action import ActionAPI

def _update_(close=1.15, balance=10000.0):
    contract = SimpleNamespace(VolumeStep=1000.0, VolumeMin=1000.0, VolumeMax=100000.0)
    portfolio = SimpleNamespace(Account=SimpleNamespace(Balance=balance), Security=SimpleNamespace(Contract=contract))
    bar = SimpleNamespace(CloseTick=SimpleNamespace(Bid=SimpleNamespace(Price=close)))
    return SimpleNamespace(Bar=bar, Portfolio=portfolio)

def test_volume_mode_caps_at_fixed_units():
    action = ActionAPI(mode=SizingMode.Volume, maximum=5000.0)
    assert action.maximum_volume(_update_()) == 5000.0

def test_balance_mode_uses_percent_of_balance():
    action = ActionAPI(mode=SizingMode.Balance, maximum=50.0)
    assert action.maximum_volume(_update_(close=1.15, balance=10000.0)) == 4000.0

def test_balance_full_exposure_uses_whole_balance():
    action = ActionAPI(mode=SizingMode.Balance, maximum=100.0)
    assert action.maximum_volume(_update_(close=1.0, balance=10000.0)) == 10000.0

def test_balance_zero_without_balance_or_price():
    assert ActionAPI(mode=SizingMode.Balance, maximum=100.0).maximum_volume(_update_(balance=0.0)) == 0.0

def test_target_signs_and_scales_by_action():
    action = ActionAPI(mode=SizingMode.Volume, maximum=10000.0)
    assert action.target(0.5, _update_()) == 5000.0
    assert action.target(-0.5, _update_()) == -5000.0

def test_target_deadzone_returns_flat():
    action = ActionAPI(mode=SizingMode.Volume, maximum=10000.0, deadzone=0.3)
    assert action.target(0.2, _update_()) == 0.0
    assert action.target(0.5, _update_()) == 5000.0

def test_target_below_minimum_volume_is_flat():
    action = ActionAPI(mode=SizingMode.Volume, maximum=10000.0)
    assert action.target(0.05, _update_()) == 0.0
