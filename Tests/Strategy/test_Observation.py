import math
from datetime import datetime
from types import SimpleNamespace

from Library.Database.Dataframe import np
from Library.Strategy.Model.Action import ActionAPI, SizingMode
from Library.Strategy.Model.Observation import ObservationAPI

def _action_(maximum=10000.0, mode=SizingMode.Fixed):
    return ActionAPI(mode=mode, maximum=maximum)

def _indicator_(value):
    return SimpleNamespace(Result=SimpleNamespace(last=lambda: value))

def _position_(volume, long, entry=10000.0, net=0.0, drawdown=0.0, runup=0.0, uid=1):
    return SimpleNamespace(Volume=volume, IsLong=long, IsShort=not long, UID=uid, EntryBalance=entry, NetPnL=SimpleNamespace(PnL=net), MaxEquityDrawdownPnL=SimpleNamespace(PnL=drawdown), MaxEquityRunupPnL=SimpleNamespace(PnL=runup))

def _update_(open=1.10, high=1.13, low=1.09, close=1.11, volume=5000.0, atr=0.01, rv=0.008, buys=None, sells=None, balance=10000.0, initial=10000.0, equity=10000.0, drawdown=0.0, runup=0.0, when=datetime(2020, 6, 15, 13, 30, 0), extra=None):
    technical = SimpleNamespace(ATR=_indicator_(atr), RV=_indicator_(rv))
    if extra:
        for key, value in extra.items(): setattr(technical, key, _indicator_(value))
    bar = SimpleNamespace(
        Timestamp=SimpleNamespace(DateTime=when),
        OpenTick=SimpleNamespace(Bid=SimpleNamespace(Price=open)),
        HighTick=SimpleNamespace(Bid=SimpleNamespace(Price=high)),
        LowTick=SimpleNamespace(Bid=SimpleNamespace(Price=low)),
        CloseTick=SimpleNamespace(Bid=SimpleNamespace(Price=close)),
        Volume=volume
    )
    portfolio = SimpleNamespace(
        BuyPositions=buys or [],
        SellPositions=sells or [],
        Account=SimpleNamespace(Balance=balance),
        InitialBalance=initial,
        Equity=equity,
        EquityDrawdown=drawdown,
        EquityRunup=runup,
        Security=SimpleNamespace(Contract=SimpleNamespace(VolumeStep=1000.0, VolumeMin=1000.0, VolumeMax=100000.0))
    )
    return SimpleNamespace(Bar=bar, Technical=technical, Portfolio=portfolio)

def test_shape_essential_and_with_moving_averages():
    assert ObservationAPI().shape() == 23
    assert ObservationAPI(moving_averages=("MA1", "MA2", "MA3")).shape() == 26

def test_encode_shape_and_dtype():
    observation = ObservationAPI(action=_action_()).encode(_update_())
    assert observation.shape == (23,)
    assert observation.dtype == np.float32

def test_timestamp_is_raw_sin_cos():
    when = datetime(2020, 6, 15, 13, 30, 0)
    observation = ObservationAPI(action=_action_()).encode(_update_(when=when))
    assert abs(observation[0] - math.sin(2.0 * math.pi * (when.month - 1) / 12)) < 1e-6
    assert abs(observation[1] - math.cos(2.0 * math.pi * (when.month - 1) / 12)) < 1e-6
    assert abs(observation[2] - math.sin(2.0 * math.pi * when.weekday() / 7)) < 1e-6

def test_drawdown_and_exposure_are_raw():
    observation = ObservationAPI(action=_action_()).encode(_update_(drawdown=-0.05, buys=[_position_(5000.0, True)]))
    assert abs(observation[10] - (-0.05)) < 1e-6
    assert abs(observation[12] - 0.5) < 1e-6

def test_flagged_features_zero_on_first_encode():
    observation = ObservationAPI(action=_action_()).encode(_update_(volume=5000.0))
    assert observation[20] == 0.0
    assert observation[8] == 0.0

def test_market_features_are_vol_scaled_log_moves():
    encoder = ObservationAPI(action=_action_())
    encoder.encode(_update_(close=1.10))
    observation = encoder.encode(_update_(open=1.105, close=1.11, rv=0.008))
    assert abs(observation[19] - math.log(1.11 / 1.10) / 0.008) < 1e-4
    assert abs(observation[16] - math.log(1.105 / 1.10) / 0.008) < 1e-4

def test_reset_clears_previous_close():
    encoder = ObservationAPI(action=_action_())
    encoder.encode(_update_(close=1.10))
    encoder.reset()
    observation = encoder.encode(_update_(open=1.105, close=1.11))
    assert observation[16] == 0.0 and observation[19] == 0.0

def test_moving_average_extends_vector():
    encoder = ObservationAPI(action=_action_(), moving_averages=("MA1",))
    observation = encoder.encode(_update_(close=1.11, atr=0.01, extra={"MA1": 1.09}))
    assert observation.shape == (24,)
    assert math.isfinite(float(observation[23]))

def test_exposure_bounded_in_percentage_mode():
    action = _action_(maximum=100.0, mode=SizingMode.Percentage)
    observation = ObservationAPI(action=action).encode(_update_(buys=[_position_(5000.0, True)], balance=10000.0, close=1.11))
    assert -1.0 <= observation[12] <= 1.0
    assert abs(observation[12] - 5000.0 / 9000.0) < 1e-6

def test_nan_indicators_encode_finite():
    observation = ObservationAPI(action=_action_(), moving_averages=("MA1",)).encode(_update_(volume=float("nan"), atr=float("nan"), rv=float("nan"), extra={"MA1": float("nan")}))
    assert np.isfinite(observation).all()