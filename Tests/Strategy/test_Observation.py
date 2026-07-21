import math
from datetime import datetime
from types import SimpleNamespace

from Library.Database.Dataframe import np
from Library.Portfolio.Sizing import SizingMode
from Library.Strategy.Hybrid.DDPG import DDPGNormalizationAPI, DDPGObservationAPI
from Library.Strategy.Model.Action import ActionAPI
from Library.Strategy.Model.Normalizer import NormalizerAPI
from Library.Strategy.Model.Observation import ObservationAPI

def _action_(exposure=100.0):
    return ActionAPI(mode=SizingMode.Balance, maximum=exposure, deadzone=0.0)

def _encoder_(action=None, momentum_features=("MOMFast", "MOMMedium", "MOMSlow"), overlap_features=(), normalize_window=200, window=1):
    return DDPGObservationAPI(action=action if action is not None else _action_(), momentum_features=momentum_features, overlap_features=overlap_features, normalize_window=normalize_window, window=window)

def _indicator_(value, window=1, previous=None):
    return SimpleNamespace(Result=SimpleNamespace(last=lambda shift=0: value if shift == 0 or previous is None else previous), Window=window)

def _position_(volume, long, entry=10000.0, net=0.0, drawdown=0.0, runup=0.0, uid=1):
    return SimpleNamespace(Volume=volume, IsLong=long, IsShort=not long, UID=uid, EntryBalance=entry, NetPnL=SimpleNamespace(PnL=net), MaxEquityDrawdownPnL=SimpleNamespace(PnL=drawdown), MaxEquityRunupPnL=SimpleNamespace(PnL=runup))

def _update_(open=1.10, high=1.13, low=1.09, close=1.11, volume=5000.0, atr=0.01, rv=0.008, buys=None, sells=None, balance=10000.0, initial=10000.0, equity=10000.0, drawdown=0.0, runup=0.0, when=datetime(2020, 6, 15, 13, 30, 0), extra=None):
    technical = SimpleNamespace(ATR=_indicator_(atr), RVFast=_indicator_(rv))
    if extra:
        for key, value in extra.items():
            setattr(technical, key, _indicator_(*value) if isinstance(value, tuple) else _indicator_(value))
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
    assert _encoder_().shape() == 30
    assert _encoder_(overlap_features=("MASlow", "MAMedium", "MAFast")).shape() == 36
    assert _encoder_(momentum_features=("MOMFast",)).shape() == 28

def test_encode_shape_and_dtype():
    observation = _encoder_(action=_action_()).encode(_update_())
    assert observation.shape == (30,)
    assert observation.dtype == np.float32

def test_window_stacks_frames_with_repeat_padding():
    encoder = _encoder_(action=_action_(), window=3)
    assert encoder.shape() == 90
    first = encoder.encode(_update_(close=1.11))
    assert first.shape == (90,) and first.dtype == np.float32
    assert np.array_equal(first[:30], first[30:60]) and np.array_equal(first[30:60], first[60:])
    second = encoder.encode(_update_(close=1.20))
    assert np.array_equal(second[:30], first[:30])
    assert np.array_equal(second[30:60], first[60:])
    assert not np.array_equal(second[60:], first[60:])
    encoder.reset()
    fresh = encoder.encode(_update_(close=1.11))
    assert np.array_equal(fresh[:30], fresh[60:])

def test_timestamp_is_raw_sin_cos():
    when = datetime(2020, 6, 15, 13, 30, 0)
    observation = _encoder_(action=_action_()).encode(_update_(when=when))
    assert abs(observation[0] - math.sin(2.0 * math.pi * (when.month - 1) / 12)) < 1e-6
    assert abs(observation[1] - math.cos(2.0 * math.pi * (when.month - 1) / 12)) < 1e-6
    assert abs(observation[2] - math.sin(2.0 * math.pi * when.weekday() / 7)) < 1e-6

def test_drawdown_and_exposure_are_raw():
    observation = _encoder_(action=_action_()).encode(_update_(drawdown=-0.05, buys=[_position_(5000.0, True)]))
    assert abs(observation[10] - (-0.05)) < 1e-6
    assert abs(observation[12] - 5000.0 / 9000.0) < 1e-6

def test_flagged_features_zero_on_first_encode():
    observation = _encoder_(action=_action_()).encode(_update_(volume=5000.0))
    assert observation[21] == 0.0
    assert observation[8] == 0.0

def test_market_features_are_vol_scaled_log_moves():
    encoder = _encoder_(action=_action_())
    encoder.encode(_update_(close=1.10))
    observation = encoder.encode(_update_(open=1.105, close=1.11, rv=0.008))
    assert abs(observation[20] - math.log(1.11 / 1.10) / 0.008) < 1e-4
    assert abs(observation[17] - math.log(1.105 / 1.10) / 0.008) < 1e-4

def test_reset_clears_previous_close():
    encoder = _encoder_(action=_action_())
    encoder.encode(_update_(close=1.10))
    encoder.reset()
    observation = encoder.encode(_update_(open=1.105, close=1.11))
    assert observation[17] == 0.0 and observation[20] == 0.0

def test_moving_average_extends_vector():
    encoder = _encoder_(action=_action_(), overlap_features=("MA20",))
    observation = encoder.encode(_update_(close=1.11, atr=0.01, extra={"MA20": 1.09}))
    assert observation.shape == (32,)
    assert math.isfinite(float(observation[30])) and math.isfinite(float(observation[31]))

def test_overlap_pair_encodes_distance_and_slope():
    encoder = _encoder_(action=_action_(), overlap_features=("MA20",))
    update = _update_(close=1.11, atr=0.01)
    update.Technical.MA20 = _indicator_(1.09, previous=1.085)
    features = []
    encoder._indicator_features_(update, features)
    assert abs(features[7][0] - (1.11 - 1.09) / 0.01) < 1e-12 and features[8][1] is True
    assert abs(features[8][0] - (1.09 - 1.085) / 0.01) < 1e-12 and features[8][1] is True

def test_overlap_slope_zero_without_history():
    encoder = _encoder_(action=_action_(), overlap_features=("MA20",))
    update = _update_(close=1.11, atr=0.01)
    update.Technical.MA20 = SimpleNamespace(Result=SimpleNamespace(last=lambda shift=0: 1.09 if shift == 0 else None), Window=1)
    features = []
    encoder._indicator_features_(update, features)
    assert features[7][0] > 0.0 and abs(features[8][0]) < 1e-12

def test_spread_is_relative_ask_bid_of_close_tick():
    encoder = _encoder_(action=_action_())
    update = _update_(close=1.1000)
    update.Bar.CloseTick.Ask = SimpleNamespace(Price=1.1002)
    features = []
    encoder._market_features_(update, features)
    value, standardized = features[5]
    assert abs(value - 0.0002 / 1.1000) < 1e-12 and standardized is True

def test_spread_zero_without_ask():
    encoder = _encoder_(action=_action_())
    features = []
    encoder._market_features_(_update_(), features)
    assert features[5] == (0.0, True)

def test_position_duration_counts_holds_and_resets():
    encoder = _encoder_(action=_action_())
    encoder.encode(_update_())
    assert encoder._position_bars_ == 0
    encoder.encode(_update_(buys=[_position_(5000.0, True, uid=1)]))
    encoder.encode(_update_(buys=[_position_(5000.0, True, uid=1)]))
    encoder.encode(_update_(buys=[_position_(5000.0, True, uid=1)]))
    assert encoder._position_bars_ == 3
    encoder.encode(_update_(sells=[_position_(5000.0, False, uid=2)]))
    assert encoder._position_bars_ == 1
    encoder.encode(_update_())
    assert encoder._position_bars_ == 0

def test_momentum_reads_roc_indicator_vol_scaled():
    encoder = _encoder_(action=_action_(), momentum_features=("MOM2",))
    observation = encoder.encode(_update_(rv=0.008, extra={"MOM2": (0.016, 2)}))
    assert abs(observation[27] - 0.016 / (0.008 * math.sqrt(2))) < 1e-6

def test_momentum_zero_without_indicator():
    observation = _encoder_(action=_action_(), momentum_features=("MOM2",)).encode(_update_(rv=0.008))
    assert observation[26] == 0.0

def test_vol_regime_is_log_ratio_of_fast_to_slow():
    observation = _encoder_(action=_action_()).encode(_update_(rv=0.008, extra={"RVSlow": 0.004}))
    assert abs(observation[25] - math.log(2.0)) < 1e-6

def test_vol_regime_zero_without_slow_indicator():
    observation = _encoder_(action=_action_()).encode(_update_(rv=0.008))
    assert observation[25] == 0.0

def test_exposure_bounded_by_reference():
    observation = _encoder_(action=_action_(exposure=100.0)).encode(_update_(buys=[_position_(5000.0, True)], balance=10000.0, close=1.11))
    assert -1.0 <= observation[12] <= 1.0
    assert abs(observation[12] - 5000.0 / 9000.0) < 1e-6

def test_nan_indicators_encode_finite():
    observation = _encoder_(action=_action_(), overlap_features=("MA20",)).encode(_update_(volume=float("nan"), atr=float("nan"), rv=float("nan"), extra={"MA20": float("nan")}))
    assert np.isfinite(observation).all()

def test_ddpg_encoder_subclasses_generic_bases():
    assert issubclass(DDPGObservationAPI, ObservationAPI)
    assert issubclass(DDPGNormalizationAPI, NormalizerAPI)

class _IdentityNormalizer_(NormalizerAPI):
    def transform(self, values, mask):
        return values.astype(np.float32)

class _ConstantObservation_(ObservationAPI):
    def _frame_size_(self):
        return 2
    def _features_(self, update):
        return [(update, True), (update * 2.0, False)]

def test_generic_base_stacks_and_shapes_without_ddpg():
    encoder = _ConstantObservation_(normalizer=_IdentityNormalizer_(), window=3)
    assert encoder.shape() == 6
    first = encoder.encode(1.0)
    assert first.shape == (6,) and first.dtype == np.float32
    assert np.array_equal(first, np.array([1.0, 2.0, 1.0, 2.0, 1.0, 2.0], dtype=np.float32))
    second = encoder.encode(5.0)
    assert np.array_equal(second[4:], np.array([5.0, 10.0], dtype=np.float32))
    assert np.array_equal(second[:2], np.array([1.0, 2.0], dtype=np.float32))
    encoder.reset()
    fresh = encoder.encode(9.0)
    assert np.array_equal(fresh, np.array([9.0, 18.0, 9.0, 18.0, 9.0, 18.0], dtype=np.float32))