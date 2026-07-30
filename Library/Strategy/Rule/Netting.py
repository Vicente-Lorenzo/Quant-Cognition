from random import Random
from typing import Union

from Library.Engine import MachineAPI
from Library.Parameter import Parameter
from Library.Portfolio import PositionType
from Library.Protocol.Action import Stream, OpenBuyPositionActionAPI, OpenSellPositionActionAPI, CloseBuyPositionActionAPI, CloseSellPositionActionAPI
from Library.Protocol.Update import UpdateID, BarUpdateAPI
from Library.Strategy.Strategy import StrategyAPI, Transform

class NettingStrategyAPI(StrategyAPI):

    Transform = Transform(Market=True, Indicators=False, Portfolio=True)
    Subscription = Stream.All & ~Stream.Tick

    _TARGETS_: tuple = (-4, -3, -2, -1, 1, 2, 3, 4)
    _FLATTEN_: int = 8
    _SEED_: int = 20260721

    def __init__(self,
                 money_management: Parameter,
                 risk_management: Parameter,
                 signal_management: Parameter,
                 technical_management: Parameter,
                 fundamental_management: Parameter,
                 sentimental_management: Parameter,
                 portfolio_management: Parameter) -> None:
        super().__init__(money_management, risk_management, signal_management, technical_management, fundamental_management, sentimental_management, portfolio_management)
        spacing = self.PortfolioManagement.ProbeSpacing if self.PortfolioManagement else None
        self._spacing_ = int(spacing[0]) if spacing else 3
        self._bars_ = 0
        self._step_ = 0
        self._random_ = Random(self._SEED_)

    def risk_management(self) -> Union[MachineAPI, None]:
        return None

    def signal_management(self) -> MachineAPI:
        signal_engine = MachineAPI(Name="Signal Management", Events=len(UpdateID))
        initialization = signal_engine.state(name="Initialization")
        waiting_signal = signal_engine.state(name="Waiting Signal")
        termination = signal_engine.state(name="Termination", end=True)
        initialization.on(event=UpdateID.Execution, to=waiting_signal, action=None, reason="Initialized")
        initialization.on(event=UpdateID.Shutdown, to=termination, action=None, reason="Abruptly Terminated")
        waiting_signal.on(event=UpdateID.BarClosed, to=waiting_signal, action=self.update_position, reason=None)
        waiting_signal.on(event=UpdateID.Shutdown, to=termination, action=None, reason="Safely Terminated")
        return signal_engine

    def _unit_(self, update: BarUpdateAPI) -> float:
        contract = update.Portfolio.Security.Contract if update.Portfolio.Security else None
        return contract.VolumeMin if contract and contract.VolumeMin else 1000.0

    def _exposure_(self, update: BarUpdateAPI, unit: float) -> int:
        longs = sum(position.Volume for position in update.Portfolio.BuyPositions)
        shorts = sum(position.Volume for position in update.Portfolio.SellPositions)
        return int(round((longs - shorts) / unit)) if unit else 0

    def _flatten_(self, update: BarUpdateAPI) -> list:
        closing = [CloseBuyPositionActionAPI(PositionID=position.UID) for position in update.Portfolio.BuyPositions]
        return closing + [CloseSellPositionActionAPI(PositionID=position.UID) for position in update.Portfolio.SellPositions]

    def _rebalance_(self, delta: int, unit: float) -> list:
        volume = abs(delta) * unit
        action = OpenBuyPositionActionAPI if delta > 0 else OpenSellPositionActionAPI
        return [action(PositionType=PositionType.Normal, Volume=volume, StopLoss=None, TakeProfit=None)]

    def update_position(self, update: BarUpdateAPI) -> Union[list, None]:
        self._bars_ += 1
        if self._bars_ % self._spacing_: return None
        unit = self._unit_(update)
        current = self._exposure_(update, unit)
        self._step_ += 1
        target = 0 if self._step_ % self._FLATTEN_ == 0 else self._random_.choice(self._TARGETS_)
        delta = target - current
        self._log_.info(lambda s=self._step_, c=current, t=target, d=delta: f"Probe Step {s}: Current {c} · Target {t} · Delta {d}")
        if not delta: return None
        if not target: return self._flatten_(update)
        return self._rebalance_(delta, unit)