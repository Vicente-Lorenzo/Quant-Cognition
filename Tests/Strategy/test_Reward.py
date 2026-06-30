import math

from Library.Strategy.Model.Reward import RewardAPI, RewardType

def test_log_return_is_exact():
    reward = RewardAPI(kind=RewardType.LogReturn, scale=1.0)
    assert abs(reward.reward(10100.0, 10000.0, 0.0) - math.log(10100.0 / 10000.0)) < 1e-12

def test_scale_is_applied():
    reward = RewardAPI(kind=RewardType.LogReturn, scale=10000.0)
    assert abs(reward.reward(10100.0, 10000.0, 0.0) - 10000.0 * math.log(1.01)) < 1e-9

def test_zero_when_no_previous_equity():
    reward = RewardAPI(kind=RewardType.LogReturn)
    assert reward.reward(10000.0, None, 0.0) == 0.0

def test_vol_scaled_first_is_zero_then_finite():
    reward = RewardAPI(kind=RewardType.VolScaledReturn)
    assert reward.reward(10100.0, 10000.0, 0.0) == 0.0
    second = reward.reward(10200.0, 10100.0, 0.0)
    assert math.isfinite(second) and second != 0.0

def test_differential_sharpe_finite_and_rewards_gains():
    reward = RewardAPI(kind=RewardType.DifferentialSharpe)
    equities = [10000.0, 10100.0, 10050.0, 10200.0, 10150.0, 10300.0]
    values = [reward.reward(equities[i], equities[i - 1], 0.0) for i in range(1, len(equities))]
    assert all(math.isfinite(v) for v in values)
    assert reward._mean_ > 0.0

def test_differential_sortino_finite():
    reward = RewardAPI(kind=RewardType.DifferentialSortino)
    equities = [10000.0, 10100.0, 9950.0, 10200.0, 10050.0]
    values = [reward.reward(equities[i], equities[i - 1], 0.0) for i in range(1, len(equities))]
    assert all(math.isfinite(v) for v in values)

def test_differential_calmar_penalized_by_drawdown():
    reward = RewardAPI(kind=RewardType.DifferentialCalmar)
    shallow = reward.reward(10100.0, 10000.0, -0.01)
    reward.reset()
    deep = reward.reward(10100.0, 10000.0, -0.50)
    assert math.isfinite(shallow) and math.isfinite(deep)
    assert deep < shallow

def test_reset_clears_state():
    reward = RewardAPI(kind=RewardType.DifferentialSharpe)
    for equity, previous in ((10100.0, 10000.0), (10200.0, 10100.0)):
        reward.reward(equity, previous, 0.0)
    reward.reset()
    assert reward._mean_ == 0.0 and reward._square_ == 0.0 and not reward._initialized_