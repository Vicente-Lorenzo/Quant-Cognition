from __future__ import annotations

import math
from typing import Any, Callable, TYPE_CHECKING

from Library.Utility.Enumeration import EnumerationAPI

if TYPE_CHECKING:
    from Library.Universe.Contract import ContractAPI
    from Library.Portfolio.Account import AccountAPI

class SizingMode(EnumerationAPI):

    Volume = 0
    Balance = 1
    Risk = 2

def calculate_conversion_rate(conversion: Any) -> float:
    rate = getattr(conversion, "Price", conversion)
    if rate is None or not rate > 0.0: raise ValueError(f"Conversion Rate: Failed · Due to no rate ({rate})")
    return float(rate)

def calculate_normalized_volume(volume: float, contract: ContractAPI, apply: Callable[[float], int] = math.floor) -> float:
    if not contract or not contract.VolumeStep or not contract.VolumeMin or not contract.VolumeMax: return volume
    normalized = apply(volume / contract.VolumeStep) * contract.VolumeStep
    return max(contract.VolumeMin, min(normalized, contract.VolumeMax))

def calculate_fixed_amount_volume(amount: float, sl_pips: float, contract: ContractAPI, quote_conversion: float = 1.0) -> float:
    if not contract or not sl_pips or not contract.PipSize or not quote_conversion: return 0.0
    return amount / (sl_pips * contract.PipSize * quote_conversion)

def calculate_fixed_fractional_volume(risk_percentage: float, sl_pips: float, account: AccountAPI, contract: ContractAPI, quote_conversion: float = 1.0) -> float:
    if not account or not account.Balance: return 0.0
    amount = account.Balance * (risk_percentage / 100.0)
    volume = calculate_fixed_amount_volume(amount, sl_pips, contract, quote_conversion)
    return calculate_normalized_volume(volume, contract)

def calculate_notional_volume(percentage: float, account: AccountAPI, contract: ContractAPI, base_conversion: float = 1.0) -> float:
    if not account or not account.Balance or not base_conversion: return 0.0
    return calculate_normalized_volume(account.Balance * (percentage / 100.0) / base_conversion, contract)

def calculate_kelly_criterion_volume(win_rate_perc: float, payoff_ratio: float, account: AccountAPI, contract: ContractAPI, sl_pips: float, fractional_kelly: float = 1.0, quote_conversion: float = 1.0) -> float:
    if not account or not account.Balance or payoff_ratio <= 0.0: return 0.0
    win_rate = win_rate_perc / 100.0
    kelly_perc = win_rate - ((1.0 - win_rate) / payoff_ratio)
    if kelly_perc <= 0.0: return 0.0
    applied_kelly_perc = (kelly_perc * fractional_kelly) * 100.0
    return calculate_fixed_fractional_volume(applied_kelly_perc, sl_pips, account, contract, quote_conversion)

def calculate_volatility_target_volume(target_volatility_perc: float, current_volatility_perc: float, account: AccountAPI, contract: ContractAPI, base_conversion: float) -> float:
    if not account or not account.Balance or not current_volatility_perc or not base_conversion or not contract or not contract.LotSize: return 0.0
    target_exposure = account.Balance * (target_volatility_perc / current_volatility_perc)
    return calculate_normalized_volume(target_exposure / base_conversion, contract)

def calculate_risk_parity_volume(inverse_variance: float, total_inverse_variance: float, total_risk_budget_perc: float, account: AccountAPI, contract: ContractAPI, base_conversion: float) -> float:
    if not account or not account.Balance or not total_inverse_variance or not base_conversion or not contract or not contract.LotSize: return 0.0
    weight = inverse_variance / total_inverse_variance
    allocated_capital = account.Balance * (total_risk_budget_perc / 100.0) * weight
    return calculate_normalized_volume(allocated_capital / base_conversion, contract)