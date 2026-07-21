from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, NamedTuple, Union, TYPE_CHECKING

from Library.Engine import MachineAPI
from Library.Logging import HandlerLoggingAPI
from Library.Protocol.Action import Stream, OpenBuyPositionActionAPI, OpenSellPositionActionAPI
from Library.Protocol.Update import (
    UpdateID,
    CompleteUpdateAPI,
    AccountUpdateAPI,
    SecurityUpdateAPI,
    TickUpdateAPI,
    BarUpdateAPI,
    OpenedBuyPositionUpdateAPI,
    OpenedSellPositionUpdateAPI,
    IncreasedBuyPositionVolumeUpdateAPI,
    IncreasedSellPositionVolumeUpdateAPI,
    DecreasedBuyPositionVolumeUpdateAPI,
    DecreasedSellPositionVolumeUpdateAPI,
    ModifiedBuyPositionStopLossUpdateAPI,
    ModifiedSellPositionStopLossUpdateAPI,
    ModifiedBuyPositionTakeProfitUpdateAPI,
    ModifiedSellPositionTakeProfitUpdateAPI,
    ClosedBuyPositionUpdateAPI,
    ClosedSellPositionUpdateAPI,
    StopLossBuyPositionUpdateAPI,
    StopLossSellPositionUpdateAPI,
    TakeProfitBuyPositionUpdateAPI,
    TakeProfitSellPositionUpdateAPI,
    MarginCallBuyPositionUpdateAPI,
    MarginCallSellPositionUpdateAPI,
    DeniedUpdateAPI,
    ExceptionUpdateAPI
)
from Library.Utility.Enumeration import EnumerationAPI

if TYPE_CHECKING:
    from Library.Parameter import Parameter

class StrategyType(EnumerationAPI):
    Download = 1
    NNFX = 2
    Trend = 3
    DDPG = 4
    Netting = 5

class Transform(NamedTuple):
    Market: bool = True
    Indicators: bool = True
    Portfolio: bool = True

class Threshold(NamedTuple):
    Lower: Union[float, None] = None
    Upper: Union[float, None] = None

class StrategyAPI(ABC):

    Transform = Transform()
    Subscription = Stream.All
    Recording: bool = False

    def __init__(self,
                 money_management: Parameter,
                 risk_management: Parameter,
                 signal_management: Parameter,
                 technical_management: Parameter,
                 fundamental_management: Parameter,
                 sentimental_management: Parameter,
                 portfolio_management: Parameter) -> None:
        self.MoneyManagement: Parameter = money_management
        self.RiskManagement: Parameter = risk_management
        self.SignalManagement: Parameter = signal_management
        self.TechnicalManagement: Parameter = technical_management
        self.FundamentalManagement: Parameter = fundamental_management
        self.SentimentalManagement: Parameter = sentimental_management
        self.PortfolioManagement: Parameter = portfolio_management
        self.DirectionalEntryThreshold: Threshold = self._threshold_("DirectionalEntryThreshold")
        self.DirectionalExitThreshold: Threshold = self._threshold_("DirectionalExitThreshold")
        self.VolumeEntryThreshold: Threshold = self._threshold_("VolumeEntryThreshold")
        self.VolumeExitThreshold: Threshold = self._threshold_("VolumeExitThreshold")
        self.Signals: list = []
        self._log_: HandlerLoggingAPI = HandlerLoggingAPI(Class=self.__class__.__name__, Subclass="Strategy Management")

    @staticmethod
    def _type_name_(obj: Any) -> str:
        return obj.Type.name if obj is not None and obj.Type is not None else "Unknown"

    @staticmethod
    def _neutral_(value: float, threshold: Threshold) -> bool:
        if threshold.Lower is None and threshold.Upper is None: return False
        lower = threshold.Lower if threshold.Lower is not None else 0.0
        upper = threshold.Upper if threshold.Upper is not None else 0.0
        return lower < value < upper

    def _threshold_(self, key: str) -> Threshold:
        bounds = self.SignalManagement[key] if self.SignalManagement is not None else None
        if not bounds: return Threshold()
        lower, upper = (list(bounds) + [None, None])[:2]
        return Threshold(Lower=float(lower) if lower is not None else None, Upper=float(upper) if upper is not None else None)

    @staticmethod
    def _signed_volume_(actions: Union[list, None]) -> float:
        if not actions: return 0.0
        return sum(action.Direction.value * (action.Volume or 0.0) for action in actions if isinstance(action, (OpenBuyPositionActionAPI, OpenSellPositionActionAPI)))

    def _emit_(self, update: BarUpdateAPI, actions: Union[list, None], raw: Union[float, None] = None) -> Union[list, None]:
        if not self.Recording: return actions
        volume = self._signed_volume_(actions)
        self.Signals.append((update.Bar.Timestamp.DateTime, raw if raw is not None else (volume > 0.0) - (volume < 0.0), volume))
        return actions

    def _log_opened_(self, update: Union[OpenedBuyPositionUpdateAPI, OpenedSellPositionUpdateAPI]) -> None:
        self._log_.alert(lambda: f"Opened {update.Direction.name} ({self._type_name_(update.Position)} Position)")

    def _log_increased_volume_(self, update: Union[IncreasedBuyPositionVolumeUpdateAPI, IncreasedSellPositionVolumeUpdateAPI]) -> None:
        self._log_.alert(lambda: f"Increased {update.Direction.name} Volume ({update.Position.Volume})")

    def _log_decreased_volume_(self, update: Union[DecreasedBuyPositionVolumeUpdateAPI, DecreasedSellPositionVolumeUpdateAPI]) -> None:
        self._log_.alert(lambda: f"Decreased {update.Direction.name} Volume ({update.Position.Volume})")

    def _log_modified_stop_loss_(self, update: Union[ModifiedBuyPositionStopLossUpdateAPI, ModifiedSellPositionStopLossUpdateAPI]) -> None:
        self._log_.alert(lambda: f"Modified {update.Direction.name} Stop-Loss ({self._type_name_(update.Position)} Position)")

    def _log_modified_take_profit_(self, update: Union[ModifiedBuyPositionTakeProfitUpdateAPI, ModifiedSellPositionTakeProfitUpdateAPI]) -> None:
        self._log_.alert(lambda: f"Modified {update.Direction.name} Take-Profit ({self._type_name_(update.Position)} Position)")

    def _log_closed_(self, update: Union[ClosedBuyPositionUpdateAPI, ClosedSellPositionUpdateAPI]) -> None:
        self._log_.alert(lambda: f"Closed {update.Direction.name} ({self._type_name_(update.Position)} Position)")

    def _log_stop_loss_(self, update: Union[StopLossBuyPositionUpdateAPI, StopLossSellPositionUpdateAPI]) -> None:
        self._log_.alert(lambda: f"Stop-Loss Hit on {update.Direction.name} ({self._type_name_(update.Position)} Position)")

    def _log_take_profit_(self, update: Union[TakeProfitBuyPositionUpdateAPI, TakeProfitSellPositionUpdateAPI]) -> None:
        self._log_.alert(lambda: f"Take-Profit Hit on {update.Direction.name} ({self._type_name_(update.Position)} Position)")

    def _log_margin_call_(self, update: Union[MarginCallBuyPositionUpdateAPI, MarginCallSellPositionUpdateAPI]) -> None:
        self._log_.error(lambda: f"Margin Call on {update.Direction.name} ({self._type_name_(update.Position)} Position)")

    def _log_denied_(self, update: DeniedUpdateAPI) -> None:
        self._log_.error(lambda: f"Action Denied: {update.ActionID.name} · {update.Reason}")

    def _log_exception_(self, update: ExceptionUpdateAPI) -> None:
        self._log_.exception(lambda: f"Exception: {update.Reason}")

    @abstractmethod
    def risk_management(self) -> Union[MachineAPI, None]:
        raise NotImplementedError

    @abstractmethod
    def signal_management(self) -> Union[MachineAPI, None]:
        raise NotImplementedError

    def strategy_management(self) -> Union[MachineAPI, None]:
        transform = self.Transform
        strategy_engine = MachineAPI(Name="Strategy Management", Events=len(UpdateID))

        initialization = strategy_engine.state(name="Initialization")
        execution = strategy_engine.state(name="Execution")
        termination = strategy_engine.state(name="Termination", end=True)

        def init_account(update: AccountUpdateAPI):
            update.Portfolio.Account = update.Account

        def init_security(update: SecurityUpdateAPI):
            update.Portfolio.Security = update.Security

        def init_indicators(update: CompleteUpdateAPI):
            if transform.Indicators:
                update.Technical.init_data(update.Market)
                update.Fundamental.init_data(update.Market)
                update.Sentimental.init_data(update.Market)

        def update_bar(update: BarUpdateAPI):
            if transform.Indicators:
                update.Technical.update_data(update.Market)
                update.Fundamental.update_data(update.Market)
                update.Sentimental.update_data(update.Market)
            if transform.Portfolio:
                update.Portfolio.update_data(update.Bar)

        def update_target(update: TickUpdateAPI):
            update.Portfolio.update_data(update.Tick)

        def update_opened(update: Union[OpenedBuyPositionUpdateAPI, OpenedSellPositionUpdateAPI]):
            update.Portfolio.update_data(update.Bar)
            update.Portfolio.Account = update.Account
            update.Portfolio.open_position(None, update.Position)
            self._log_opened_(update)

        def update_increased_volume(update: Union[IncreasedBuyPositionVolumeUpdateAPI, IncreasedSellPositionVolumeUpdateAPI]):
            update.Portfolio.update_data(update.Bar)
            update.Portfolio.Account = update.Account
            update.Portfolio.modify_position(update.Position)
            self._log_increased_volume_(update)

        def update_decreased_volume(update: Union[DecreasedBuyPositionVolumeUpdateAPI, DecreasedSellPositionVolumeUpdateAPI]):
            update.Portfolio.update_data(update.Bar)
            update.Portfolio.Account = update.Account
            update.Portfolio.close_position(update.Position.UID, update.Position, update.Trade)
            self._log_decreased_volume_(update)

        def update_modified_stop_loss(update: Union[ModifiedBuyPositionStopLossUpdateAPI, ModifiedSellPositionStopLossUpdateAPI]):
            update.Portfolio.update_data(update.Bar)
            update.Portfolio.Account = update.Account
            update.Portfolio.modify_position(update.Position)
            self._log_modified_stop_loss_(update)

        def update_modified_take_profit(update: Union[ModifiedBuyPositionTakeProfitUpdateAPI, ModifiedSellPositionTakeProfitUpdateAPI]):
            update.Portfolio.update_data(update.Bar)
            update.Portfolio.Account = update.Account
            update.Portfolio.modify_position(update.Position)
            self._log_modified_take_profit_(update)

        def update_closed(update: Union[ClosedBuyPositionUpdateAPI, ClosedSellPositionUpdateAPI]):
            update.Portfolio.update_data(update.Bar)
            update.Portfolio.Account = update.Account
            update.Portfolio.close_position(update.Position.UID, None, update.Trade)
            self._log_closed_(update)

        def update_stop_loss(update: Union[StopLossBuyPositionUpdateAPI, StopLossSellPositionUpdateAPI]):
            update.Portfolio.update_data(update.Bar)
            update.Portfolio.Account = update.Account
            update.Portfolio.close_position(update.Position.UID, None, update.Trade)
            self._log_stop_loss_(update)

        def update_take_profit(update: Union[TakeProfitBuyPositionUpdateAPI, TakeProfitSellPositionUpdateAPI]):
            update.Portfolio.update_data(update.Bar)
            update.Portfolio.Account = update.Account
            update.Portfolio.close_position(update.Position.UID, None, update.Trade)
            self._log_take_profit_(update)

        def update_margin_call(update: Union[MarginCallBuyPositionUpdateAPI, MarginCallSellPositionUpdateAPI]):
            update.Portfolio.update_data(update.Bar)
            update.Portfolio.Account = update.Account
            update.Portfolio.close_position(update.Position.UID, None, update.Trade)
            self._log_margin_call_(update)

        def update_opened_order(update: Any):
            update.Portfolio.update_data(update.Bar)
            update.Portfolio.Account = update.Account
            update.Portfolio.open_order(update.Order)
            self._log_.alert(lambda: f"Opened {update.Order.Type.name} {update.Order.Direction.name} Order")

        def update_modified_order(update: Any):
            update.Portfolio.update_data(update.Bar)
            update.Portfolio.Account = update.Account
            update.Portfolio.modify_order(update.Order)
            self._log_.alert(lambda: f"Modified {update.Order.Type.name} {update.Order.Direction.name} Order")

        def update_closed_order(update: Any):
            update.Portfolio.update_data(update.Bar)
            update.Portfolio.Account = update.Account
            update.Portfolio.close_order(update.Order.UID)
            self._log_.alert(lambda: f"Closed {update.Order.Type.name} {update.Order.Direction.name} Order")

        def update_filled_order(update: Any):
            update.Portfolio.update_data(update.Bar)
            update.Portfolio.Account = update.Account
            update.Portfolio.close_order(update.Order.UID)
            self._log_.alert(lambda: f"Filled {update.Order.Type.name} {update.Order.Direction.name} Order")

        def update_expired_order(update: Any):
            update.Portfolio.update_data(update.Bar)
            update.Portfolio.Account = update.Account
            update.Portfolio.close_order(update.Order.UID)
            self._log_.alert(lambda: f"Expired {update.Order.Type.name} {update.Order.Direction.name} Order")

        initialization.on(event=UpdateID.Account, to=initialization, action=init_account, reason="Account Initialized")
        initialization.on(event=UpdateID.Security, to=initialization, action=init_security, reason="Security Initialized")
        initialization.on(event=UpdateID.Execution, to=execution, action=init_indicators, reason="Initialized")
        initialization.on(event=UpdateID.Denied, to=initialization, action=self._log_denied_, reason=None)
        initialization.on(event=UpdateID.Exception, to=termination, action=self._log_exception_, reason="Exception")
        initialization.on(event=UpdateID.Shutdown, to=termination, action=None, reason="Abruptly Terminated")

        execution.on(event=UpdateID.Account, to=execution, action=init_account, reason="Account Updated")
        execution.on(event=UpdateID.Security, to=execution, action=init_security, reason="Security Updated")
        execution.on(event=UpdateID.BarClosed, to=execution, action=update_bar, reason=None)
        execution.on(event=UpdateID.AskAboveTarget, to=execution, action=update_target, reason=None)
        execution.on(event=UpdateID.AskBelowTarget, to=execution, action=update_target, reason=None)
        execution.on(event=UpdateID.BidAboveTarget, to=execution, action=update_target, reason=None)
        execution.on(event=UpdateID.BidBelowTarget, to=execution, action=update_target, reason=None)

        execution.on(event=UpdateID.OpenedBuyPosition, to=execution, action=update_opened, reason="Opened Buy Position")
        execution.on(event=UpdateID.OpenedSellPosition, to=execution, action=update_opened, reason="Opened Sell Position")
        execution.on(event=UpdateID.IncreasedBuyPositionVolume, to=execution, action=update_increased_volume, reason="Increased Buy Volume")
        execution.on(event=UpdateID.IncreasedSellPositionVolume, to=execution, action=update_increased_volume, reason="Increased Sell Volume")
        execution.on(event=UpdateID.DecreasedBuyPositionVolume, to=execution, action=update_decreased_volume, reason="Decreased Buy Volume")
        execution.on(event=UpdateID.DecreasedSellPositionVolume, to=execution, action=update_decreased_volume, reason="Decreased Sell Volume")
        execution.on(event=UpdateID.ModifiedBuyPositionStopLoss, to=execution, action=update_modified_stop_loss, reason="Modified Buy Stop-Loss")
        execution.on(event=UpdateID.ModifiedSellPositionStopLoss, to=execution, action=update_modified_stop_loss, reason="Modified Sell Stop-Loss")
        execution.on(event=UpdateID.ModifiedBuyPositionTakeProfit, to=execution, action=update_modified_take_profit, reason="Modified Buy Take-Profit")
        execution.on(event=UpdateID.ModifiedSellPositionTakeProfit, to=execution, action=update_modified_take_profit, reason="Modified Sell Take-Profit")
        execution.on(event=UpdateID.ClosedBuyPosition, to=execution, action=update_closed, reason="Closed Buy Position")
        execution.on(event=UpdateID.ClosedSellPosition, to=execution, action=update_closed, reason="Closed Sell Position")
        execution.on(event=UpdateID.StopLossBuyPosition, to=execution, action=update_stop_loss, reason="Stop-Loss Hit on Buy")
        execution.on(event=UpdateID.StopLossSellPosition, to=execution, action=update_stop_loss, reason="Stop-Loss Hit on Sell")
        execution.on(event=UpdateID.TakeProfitBuyPosition, to=execution, action=update_take_profit, reason="Take-Profit Hit on Buy")
        execution.on(event=UpdateID.TakeProfitSellPosition, to=execution, action=update_take_profit, reason="Take-Profit Hit on Sell")
        execution.on(event=UpdateID.MarginCallBuyPosition, to=execution, action=update_margin_call, reason="Margin Call on Buy")
        execution.on(event=UpdateID.MarginCallSellPosition, to=execution, action=update_margin_call, reason="Margin Call on Sell")

        execution.on(event=UpdateID.OpenedBuyStopOrder, to=execution, action=update_opened_order, reason="Opened Buy Stop Order")
        execution.on(event=UpdateID.OpenedSellStopOrder, to=execution, action=update_opened_order, reason="Opened Sell Stop Order")
        execution.on(event=UpdateID.ModifiedBuyStopOrderVolume, to=execution, action=update_modified_order, reason="Modified Buy Stop Order Volume")
        execution.on(event=UpdateID.ModifiedBuyStopOrderStopPrice, to=execution, action=update_modified_order, reason="Modified Buy Stop Order Stop-Price")
        execution.on(event=UpdateID.ModifiedBuyStopOrderStopLoss, to=execution, action=update_modified_order, reason="Modified Buy Stop Order Stop-Loss")
        execution.on(event=UpdateID.ModifiedBuyStopOrderTakeProfit, to=execution, action=update_modified_order, reason="Modified Buy Stop Order Take-Profit")
        execution.on(event=UpdateID.ModifiedSellStopOrderVolume, to=execution, action=update_modified_order, reason="Modified Sell Stop Order Volume")
        execution.on(event=UpdateID.ModifiedSellStopOrderStopPrice, to=execution, action=update_modified_order, reason="Modified Sell Stop Order Stop-Price")
        execution.on(event=UpdateID.ModifiedSellStopOrderStopLoss, to=execution, action=update_modified_order, reason="Modified Sell Stop Order Stop-Loss")
        execution.on(event=UpdateID.ModifiedSellStopOrderTakeProfit, to=execution, action=update_modified_order, reason="Modified Sell Stop Order Take-Profit")
        execution.on(event=UpdateID.ClosedBuyStopOrder, to=execution, action=update_closed_order, reason="Closed Buy Stop Order")
        execution.on(event=UpdateID.ClosedSellStopOrder, to=execution, action=update_closed_order, reason="Closed Sell Stop Order")
        execution.on(event=UpdateID.FilledBuyStopOrder, to=execution, action=update_filled_order, reason="Filled Buy Stop Order")
        execution.on(event=UpdateID.FilledSellStopOrder, to=execution, action=update_filled_order, reason="Filled Sell Stop Order")
        execution.on(event=UpdateID.ExpiredBuyStopOrder, to=execution, action=update_expired_order, reason="Expired Buy Stop Order")
        execution.on(event=UpdateID.ExpiredSellStopOrder, to=execution, action=update_expired_order, reason="Expired Sell Stop Order")

        execution.on(event=UpdateID.OpenedBuyLimitOrder, to=execution, action=update_opened_order, reason="Opened Buy Limit Order")
        execution.on(event=UpdateID.OpenedSellLimitOrder, to=execution, action=update_opened_order, reason="Opened Sell Limit Order")
        execution.on(event=UpdateID.ModifiedBuyLimitOrderVolume, to=execution, action=update_modified_order, reason="Modified Buy Limit Order Volume")
        execution.on(event=UpdateID.ModifiedBuyLimitOrderLimitPrice, to=execution, action=update_modified_order, reason="Modified Buy Limit Order Limit-Price")
        execution.on(event=UpdateID.ModifiedBuyLimitOrderStopLoss, to=execution, action=update_modified_order, reason="Modified Buy Limit Order Stop-Loss")
        execution.on(event=UpdateID.ModifiedBuyLimitOrderTakeProfit, to=execution, action=update_modified_order, reason="Modified Buy Limit Order Take-Profit")
        execution.on(event=UpdateID.ModifiedSellLimitOrderVolume, to=execution, action=update_modified_order, reason="Modified Sell Limit Order Volume")
        execution.on(event=UpdateID.ModifiedSellLimitOrderLimitPrice, to=execution, action=update_modified_order, reason="Modified Sell Limit Order Limit-Price")
        execution.on(event=UpdateID.ModifiedSellLimitOrderStopLoss, to=execution, action=update_modified_order, reason="Modified Sell Limit Order Stop-Loss")
        execution.on(event=UpdateID.ModifiedSellLimitOrderTakeProfit, to=execution, action=update_modified_order, reason="Modified Sell Limit Order Take-Profit")
        execution.on(event=UpdateID.ClosedBuyLimitOrder, to=execution, action=update_closed_order, reason="Closed Buy Limit Order")
        execution.on(event=UpdateID.ClosedSellLimitOrder, to=execution, action=update_closed_order, reason="Closed Sell Limit Order")
        execution.on(event=UpdateID.FilledBuyLimitOrder, to=execution, action=update_filled_order, reason="Filled Buy Limit Order")
        execution.on(event=UpdateID.FilledSellLimitOrder, to=execution, action=update_filled_order, reason="Filled Sell Limit Order")
        execution.on(event=UpdateID.ExpiredBuyLimitOrder, to=execution, action=update_expired_order, reason="Expired Buy Limit Order")
        execution.on(event=UpdateID.ExpiredSellLimitOrder, to=execution, action=update_expired_order, reason="Expired Sell Limit Order")

        execution.on(event=UpdateID.OpenedBuyStopLimitOrder, to=execution, action=update_opened_order, reason="Opened Buy Stop-Limit Order")
        execution.on(event=UpdateID.OpenedSellStopLimitOrder, to=execution, action=update_opened_order, reason="Opened Sell Stop-Limit Order")
        execution.on(event=UpdateID.ModifiedBuyStopLimitOrderVolume, to=execution, action=update_modified_order, reason="Modified Buy Stop-Limit Order Volume")
        execution.on(event=UpdateID.ModifiedBuyStopLimitOrderStopPrice, to=execution, action=update_modified_order, reason="Modified Buy Stop-Limit Order Stop-Price")
        execution.on(event=UpdateID.ModifiedBuyStopLimitOrderLimitPrice, to=execution, action=update_modified_order, reason="Modified Buy Stop-Limit Order Limit-Price")
        execution.on(event=UpdateID.ModifiedBuyStopLimitOrderStopLoss, to=execution, action=update_modified_order, reason="Modified Buy Stop-Limit Order Stop-Loss")
        execution.on(event=UpdateID.ModifiedBuyStopLimitOrderTakeProfit, to=execution, action=update_modified_order, reason="Modified Buy Stop-Limit Order Take-Profit")
        execution.on(event=UpdateID.ModifiedSellStopLimitOrderVolume, to=execution, action=update_modified_order, reason="Modified Sell Stop-Limit Order Volume")
        execution.on(event=UpdateID.ModifiedSellStopLimitOrderStopPrice, to=execution, action=update_modified_order, reason="Modified Sell Stop-Limit Order Stop-Price")
        execution.on(event=UpdateID.ModifiedSellStopLimitOrderLimitPrice, to=execution, action=update_modified_order, reason="Modified Sell Stop-Limit Order Limit-Price")
        execution.on(event=UpdateID.ModifiedSellStopLimitOrderStopLoss, to=execution, action=update_modified_order, reason="Modified Sell Stop-Limit Order Stop-Loss")
        execution.on(event=UpdateID.ModifiedSellStopLimitOrderTakeProfit, to=execution, action=update_modified_order, reason="Modified Sell Stop-Limit Order Take-Profit")
        execution.on(event=UpdateID.ClosedBuyStopLimitOrder, to=execution, action=update_closed_order, reason="Closed Buy Stop-Limit Order")
        execution.on(event=UpdateID.ClosedSellStopLimitOrder, to=execution, action=update_closed_order, reason="Closed Sell Stop-Limit Order")
        execution.on(event=UpdateID.FilledBuyStopLimitOrder, to=execution, action=update_filled_order, reason="Filled Buy Stop-Limit Order")
        execution.on(event=UpdateID.FilledSellStopLimitOrder, to=execution, action=update_filled_order, reason="Filled Sell Stop-Limit Order")
        execution.on(event=UpdateID.ExpiredBuyStopLimitOrder, to=execution, action=update_expired_order, reason="Expired Buy Stop-Limit Order")
        execution.on(event=UpdateID.ExpiredSellStopLimitOrder, to=execution, action=update_expired_order, reason="Expired Sell Stop-Limit Order")

        execution.on(event=UpdateID.Denied, to=execution, action=self._log_denied_, reason=None)
        execution.on(event=UpdateID.Exception, to=termination, action=self._log_exception_, reason="Exception")
        execution.on(event=UpdateID.Shutdown, to=termination, action=None, reason="Safely Terminated")

        return strategy_engine