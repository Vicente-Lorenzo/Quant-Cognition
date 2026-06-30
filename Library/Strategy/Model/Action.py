from __future__ import annotations

from typing import TYPE_CHECKING

from Library.Portfolio.Sizing import calculate_normalized_volume
from Library.Utility.Enumeration import EnumerationAPI

if TYPE_CHECKING:
    from Library.Protocol.Update import BarUpdateAPI

class SizingMode(EnumerationAPI):
    Fixed = 0
    Percentage = 1

class ActionAPI:
    """
    Action decoder — maps the agent output a in [-1, 1] to a signed target volume.

    The agent emits a scale-free signed exposure fraction; this decoder turns it
    into a broker volume:
      - Deadzone: |a| < SizingDeadzone -> 0 (flat) to suppress churn from tiny actions.
      - MaxVolume from the sizing config (scale-free, configurable):
          Fixed       -> SizingMax is a volume cap.
          Percentage  -> SizingMax is a percent of account balance, converted to a
                         notional and divided by price to obtain a volume.
      - target = floor-normalize(|a| * MaxVolume) to the contract volume step,
        clamped to [VolumeMin, VolumeMax]; below VolumeMin -> 0 (flat). The sign of
        the target follows the sign of a.

    The downstream position controller (in ModelStrategyAPI) turns the signed target
    into open / scale-out / hold / reverse / close orders under a <= 1 position rule.
    """

    def __init__(self, mode: SizingMode = SizingMode.Fixed, maximum: float = 1.0, deadzone: float = 0.0) -> None:
        self._mode_ = mode
        self._maximum_ = maximum
        self._deadzone_ = deadzone

    def maximum_volume(self, update: BarUpdateAPI) -> float:
        contract = update.Portfolio.Security.Contract
        if self._mode_ == SizingMode.Percentage:
            balance = update.Portfolio.Account.Balance if update.Portfolio.Account else 0.0
            price = update.Bar.CloseTick.Bid.Price
            if not balance or not price: return 0.0
            return calculate_normalized_volume(balance * (self._maximum_ / 100.0) / price, contract)
        return calculate_normalized_volume(self._maximum_, contract)

    def target(self, action: float, update: BarUpdateAPI) -> float:
        if abs(action) < self._deadzone_: return 0.0
        contract = update.Portfolio.Security.Contract
        raw = abs(action) * self.maximum_volume(update)
        if raw < contract.VolumeMin: return 0.0
        volume = calculate_normalized_volume(raw, contract)
        return volume if action > 0.0 else -volume