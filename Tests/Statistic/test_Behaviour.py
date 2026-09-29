import pytest

from Library.Database.Dataframe import np
from Library.Statistic.Behaviour import exposure_beta, null, persistence, regime, runs, sidedness

def test_sidedness_counts_active_time_and_the_weaker_side():
    assert sidedness(np.array([1.0, 1.0, -1.0, 0.0])) == pytest.approx((0.75, 2 / 3, 1 / 3))
    assert sidedness(np.zeros(3)) == (0.0, 0.0, 0.0)

def test_runs_skip_flat_time_and_flips_count_direction_changes():
    lengths, directions = runs(np.array([1.0, 1.0, 0.0, -1.0, -1.0, -1.0, 1.0]))
    assert lengths.tolist() == [2, 3, 1] and directions.tolist() == [1, -1, 1]
    summary = persistence(np.array([1.0] * 48 + [0.0] * 5 + [-1.0] * 24), bars_per_day=24.0)
    assert summary["Runs"] == 2 and summary["Flips"] == 1 and summary["MeanHoldDays"] == pytest.approx(1.5) and summary["LongestDays"] == pytest.approx(2.0)
    assert summary["HeldBeyond1Days"] == pytest.approx(1.0) and summary["HeldBeyond7Days"] == 0.0

def test_regime_weights_each_year_by_its_move_and_skips_thin_years():
    years = np.repeat([2020, 2021, 2022], [200, 200, 50])
    closes = np.concatenate((np.linspace(1.0, 1.1, 200), np.linspace(1.1, 1.0, 200), np.linspace(1.0, 2.0, 50)))
    right = np.concatenate((np.ones(200), -np.ones(200), -np.ones(50)))
    assert regime(right, closes, years) == pytest.approx(100.0)
    assert regime(np.ones(450), closes, years) == pytest.approx(100.0 * 0.1 / (0.1 + 0.1 / 1.1))
    assert regime(np.zeros(450), closes, years) is None

def test_a_policy_that_never_changes_side_is_no_better_than_its_own_rotations():
    years = np.repeat([2020, 2021], 200)
    closes = np.concatenate((np.linspace(1.0, 1.1, 200), np.linspace(1.1, 1.2, 200)))
    result = null(np.ones(400), closes, years, draws=50)
    assert result["Regime"] == pytest.approx(100.0) and result["NullMedian"] == pytest.approx(100.0) and result["P"] == pytest.approx(1.0)

def test_exposure_beta_recovers_a_linear_relation():
    market = np.array([0.1, -0.05, 0.02, 0.08, -0.12])
    beta, alpha = exposure_beta(2.0 * market + 0.01, market)
    assert beta == pytest.approx(2.0) and alpha == pytest.approx(0.01)
    assert exposure_beta(np.array([0.1]), np.array([0.1])) == (None, None)