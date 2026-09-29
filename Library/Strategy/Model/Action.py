from __future__ import annotations

from typing import TYPE_CHECKING

from Library.Portfolio.Sizing import SizingMode, calculate_conversion_rate, calculate_normalized_volume, calculate_notional_volume

if TYPE_CHECKING:
    from Library.Protocol.Update import BarUpdateAPI

class ActionAPI:
    """
    Action decoder — maps the agent output a in [-1, 1] to a signed target volume.

    The agent emits a scale-free signed exposure fraction; this decoder turns it
    into a broker volume:
      - Deadzone: |a| < deadzone -> 0 (flat) to suppress churn from tiny actions.
      - MaxVolume from the sizing config (scale-free, configurable):
          Volume   -> maximum is a raw volume cap (units).
          Balance  -> maximum is a percent of account balance, a notional in the account
                      currency, divided by the base-to-account rate to obtain a volume.
      - target = floor-normalize(|a| * MaxVolume) to the contract volume step, clamped
        to [VolumeMin, VolumeMax]; below VolumeMin -> 0 (flat). The sign of the target
        follows the sign of a. The Risk sizing mode is stop-based money management and
        is handled by the rule strategies, not by this decoder.

    The downstream position controller (the consuming strategy) turns the signed target
    into open / scale-out / hold / reverse / close orders under a <= 1 position rule.
    """

    def __init__(self, mode: SizingMode, maximum: float, deadzone: float) -> None:
        self._mode_ = mode
        self._maximum_ = maximum
        self._deadzone_ = deadzone

    def maximum_volume(self, update: BarUpdateAPI) -> float:
        contract = update.Portfolio.Security.Contract
        if self._mode_ == SizingMode.Balance:
            return calculate_notional_volume(self._maximum_, update.Portfolio.Account, contract, calculate_conversion_rate(update.Bar.ClosePoint.BidTick.BidBaseConversion))
        return calculate_normalized_volume(self._maximum_, contract)

    def target(self, action: float, update: BarUpdateAPI) -> float:
        if abs(action) < self._deadzone_: return 0.0
        contract = update.Portfolio.Security.Contract
        raw = abs(action) * self.maximum_volume(update)
        if raw < contract.VolumeMin: return 0.0
        volume = calculate_normalized_volume(raw, contract)
        return volume if action > 0.0 else -volume