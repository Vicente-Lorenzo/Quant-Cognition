from __future__ import annotations

import math
from typing import Callable, TYPE_CHECKING

from Library.Utility.Enumeration import EnumerationAPI

if TYPE_CHECKING:
    from Library.Universe.Contract import ContractAPI
    from Library.Portfolio.Account import AccountAPI

class SizingMode(EnumerationAPI):

    Volume = 0
    Balance = 1
    Risk = 2

def calculate_normalized_volume(volume: float, contract: ContractAPI, apply: Callable[[float], int] = math.floor) -> float:
    if not contract or not contract.VolumeStep or not contract.VolumeMin or not contract.VolumeMax: return volume
    normalized = apply(volume / contract.VolumeStep) * contract.VolumeStep
    return max(contract.VolumeMin, min(normalized, contract.VolumeMax))

def calculate_fixed_amount_volume(amount: float, sl_pips: float, contract: ContractAPI) -> float:
    if not contract or not sl_pips or not contract.PipSize: return 0.0
    volume = amount / (sl_pips * contract.PipSize)
    return volume

def calculate_fixed_fractional_volume(risk_percentage: float, sl_pips: float, account: AccountAPI, contract: ContractAPI) -> float:
    if not account or not account.Balance: return 0.0
    amount = account.Balance * (risk_percentage / 100.0)
    volume = calculate_fixed_amount_volume(amount, sl_pips, contract)
    return calculate_normalized_volume(volume, contract)

def calculate_kelly_criterion_volume(win_rate_perc: float, payoff_ratio: float, account: AccountAPI, contract: ContractAPI, sl_pips: float, fractional_kelly: float = 1.0) -> float:
    if not account or not account.Balance or payoff_ratio <= 0.0: return 0.0
    win_rate = win_rate_perc / 100.0
    kelly_perc = win_rate - ((1.0 - win_rate) / payoff_ratio)
    if kelly_perc <= 0.0: return 0.0
    applied_kelly_perc = (kelly_perc * fractional_kelly) * 100.0
    return calculate_fixed_fractional_volume(applied_kelly_perc, sl_pips, account, contract)

def calculate_volatility_target_volume(target_volatility_perc: float, current_volatility_perc: float, account: AccountAPI, contract: ContractAPI, current_price: float) -> float:
    if not account or not account.Balance or not current_volatility_perc or not current_price or not contract or not contract.LotSize: return 0.0
    target_exposure = account.Balance * (target_volatility_perc / current_volatility_perc)
    volume = target_exposure / current_price
    return calculate_normalized_volume(volume, contract)

def calculate_risk_parity_volume(inverse_variance: float, total_inverse_variance: float, total_risk_budget_perc: float, account: AccountAPI, contract: ContractAPI, current_price: float) -> float:
    if not account or not account.Balance or not total_inverse_variance or not current_price or not contract or not contract.LotSize: return 0.0
    weight = inverse_variance / total_inverse_variance
    allocated_capital = account.Balance * (total_risk_budget_perc / 100.0) * weight
    volume = allocated_capital / current_price
    return calculate_normalized_volume(volume, contract)