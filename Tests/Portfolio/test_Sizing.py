import math

import pytest

from Library.Universe.Contract import ContractAPI
from Library.Portfolio.Account import AccountAPI
from Library.Market.Price import PriceAPI
from Library.Portfolio.Sizing import (
    calculate_conversion_rate,
    calculate_notional_volume,
    calculate_normalized_volume,
    calculate_fixed_amount_volume,
    calculate_fixed_fractional_volume,
    calculate_kelly_criterion_volume,
    calculate_volatility_target_volume,
    calculate_risk_parity_volume
)

def test_calculate_normalized_volume():
    contract = ContractAPI(VolumeStep=1000.0, VolumeMin=1000.0, VolumeMax=10000000.0)
    assert calculate_normalized_volume(1500.0, contract) == 1000.0
    assert calculate_normalized_volume(1500.0, contract, apply=math.ceil) == 2000.0
    assert calculate_normalized_volume(500.0, contract) == 1000.0
    assert calculate_normalized_volume(15000000.0, contract) == 10000000.0

def test_calculate_fixed_amount_volume():
    contract = ContractAPI(PipSize=0.0001, LotSize=100000.0)
    # Risk 100 USD on 50 pips. 50 pips * 0.0001 = 0.0050 distance.
    # 100 / 0.0050 = 20000 volume base units.
    assert calculate_fixed_amount_volume(100.0, 50.0, contract) == 20000.0

def test_calculate_fixed_fractional_volume():
    contract = ContractAPI(PipSize=0.0001, LotSize=100000.0, VolumeStep=1000.0, VolumeMin=1000.0, VolumeMax=1000000.0)
    account = AccountAPI(Balance=10000.0)
    # Risk 1% of 10000 = 100. sl_pips = 50. Output should be 20000.
    assert calculate_fixed_fractional_volume(1.0, 50.0, account, contract) == 20000.0

def test_calculate_kelly_criterion_volume():
    contract = ContractAPI(PipSize=0.0001, LotSize=100000.0, VolumeStep=1000.0, VolumeMin=1000.0, VolumeMax=1000000.0)
    account = AccountAPI(Balance=10000.0)
    # win_rate = 60%, payoff = 2.0. Kelly = 0.6 - (0.4 / 2.0) = 0.6 - 0.2 = 0.4 (40%)
    # 40% of 10000 = 4000. sl_pips = 50. Volume = 4000 / (50 * 0.0001) = 4000 / 0.005 = 800000.
    assert calculate_kelly_criterion_volume(60.0, 2.0, account, contract, 50.0) == 800000.0
    # Half kelly = 20%. Volume = 400000.
    assert calculate_kelly_criterion_volume(60.0, 2.0, account, contract, 50.0, fractional_kelly=0.5) == 400000.0
    # Losing strategy: win_rate = 30%, payoff = 1.0. Kelly = 0.3 - 0.7 = -0.4. Should be 0.
    assert calculate_kelly_criterion_volume(30.0, 1.0, account, contract, 50.0) == 0.0

def test_calculate_volatility_target_volume():
    contract = ContractAPI(LotSize=100000.0, VolumeStep=1000.0, VolumeMin=1000.0, VolumeMax=1000000.0)
    account = AccountAPI(Balance=10000.0)
    # Target 10% vol, current is 20%. So target exposure = 10000 * (10/20) = 5000.
    # Current price = 1.05. Volume = 5000 / 1.05 = 4761.9. Normalized (step 1000, floor) = 4000.
    assert calculate_volatility_target_volume(10.0, 20.0, account, contract, 1.05) == 4000.0

def test_calculate_risk_parity_volume():
    contract = ContractAPI(LotSize=100000.0, VolumeStep=1000.0, VolumeMin=1000.0, VolumeMax=1000000.0)
    account = AccountAPI(Balance=10000.0)
    # Asset variance is high, inverse_variance = 0.2. Total inverse variance = 1.0. Weight = 0.2.
    # Risk budget = 100%. Allocated capital = 10000 * 100% * 0.2 = 2000.
    # Current price = 1.05. Volume = 2000 / 1.05 = 1904.7. Normalized = 1000.
    assert calculate_risk_parity_volume(0.2, 1.0, 100.0, account, contract, 1.05) == 1000.0

def test_risk_is_measured_in_the_account_currency_through_the_quote_conversion():
    contract = ContractAPI(PipSize=0.01, LotSize=100000.0, VolumeStep=1000.0, VolumeMin=1000.0, VolumeMax=10000000.0)
    account = AccountAPI(Balance=10000.0)
    volume = calculate_fixed_fractional_volume(1.0, 50.0, account, contract, 1.0 / 160.0)
    assert volume == 32000.0 and volume * 50.0 * contract.PipSize / 160.0 == pytest.approx(100.0)

def test_a_notional_is_sized_through_the_base_conversion():
    contract = ContractAPI(LotSize=100000.0, VolumeStep=1000.0, VolumeMin=1000.0, VolumeMax=10000000.0)
    assert calculate_notional_volume(100.0, AccountAPI(Balance=10000.0), contract, 0.92) == 10000.0
    assert calculate_notional_volume(100.0, AccountAPI(Balance=10000.0), contract, 1.0) == 10000.0
    assert calculate_notional_volume(50.0, AccountAPI(Balance=10000.0), contract, 1.1) == 4000.0

def test_a_conversion_rate_must_be_known():
    assert calculate_conversion_rate(PriceAPI(Price=0.9)) == 0.9 and calculate_conversion_rate(1.25) == 1.25
    for unknown in (None, PriceAPI(Price=None), 0.0, float("nan")):
        with pytest.raises(ValueError): calculate_conversion_rate(unknown)