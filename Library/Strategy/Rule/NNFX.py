from __future__ import annotations

from typing import Any, Union, TYPE_CHECKING

from Library.Engine.Machine import MachineAPI
from Library.Market.Price import Direction
from Library.Portfolio.Position import PositionType
from Library.Portfolio.Sizing import SizingMode, calculate_fixed_fractional_volume, calculate_normalized_volume
from Library.Protocol.Action import (
    Stream,
    AskBelowTargetActionAPI,
    BidAboveTargetActionAPI,
    OpenBuyPositionActionAPI,
    OpenSellPositionActionAPI,
    DecreaseBuyPositionVolumeActionAPI,
    DecreaseSellPositionVolumeActionAPI,
    ModifyBuyPositionStopLossActionAPI,
    ModifySellPositionStopLossActionAPI,
    CloseBuyPositionActionAPI,
    CloseSellPositionActionAPI
)
from Library.Protocol.Update import (
    UpdateID,
    TickUpdateAPI,
    BarUpdateAPI,
    OpenedBuyPositionUpdateAPI,
    OpenedSellPositionUpdateAPI,
    DecreasedBuyPositionVolumeUpdateAPI,
    DecreasedSellPositionVolumeUpdateAPI,
    ModifiedBuyPositionStopLossUpdateAPI,
    ModifiedSellPositionStopLossUpdateAPI
)
from Library.Strategy.Strategy import StrategyAPI

if TYPE_CHECKING:
    from Library.Parameter import Parameter

class NNFXStrategyAPI(StrategyAPI):

    Subscription = Stream.All & ~Stream.Tick

    def __init__(self,
                 money_management: Parameter,
                 risk_management: Parameter,
                 signal_management: Parameter,
                 technical_management: Parameter,
                 fundamental_management: Parameter,
                 sentimental_management: Parameter,
                 portfolio_management: Parameter) -> None:
        super().__init__(money_management, risk_management, signal_management, technical_management, fundamental_management, sentimental_management, portfolio_management)
        self._stop_loss_scale_, = self.RiskManagement.StopLossScale
        self._scaling_out_scale_, = self.RiskManagement.ScalingOutScale
        self._scaling_out_percentage_, = self.RiskManagement.ScalingOutPercentage
        self._trailing_stop_loss_scale_, = self.RiskManagement.TrailingStopLossScale
        self._trailing_stop_loss_step_, = self.RiskManagement.TrailingStopLossStep
        self._stagnation_stop_loss_, = self.RiskManagement.StagnationStopLoss
        self._use_stop_loss_ = self._positive_(self._stop_loss_scale_)
        self._sizing_atr_scale_ = self._stop_loss_scale_ or 0.0
        self._use_scaling_out_ = self._positive_(self._scaling_out_scale_) and self._positive_(self._scaling_out_percentage_)
        self._use_trailing_stop_loss_ = self._positive_(self._trailing_stop_loss_scale_) and self._use_stop_loss_
        self._use_stagnation_ = self._positive_(self._stagnation_stop_loss_)
        self._managed_risk_ = self._use_stop_loss_ or self._use_scaling_out_ or self._use_trailing_stop_loss_ or self._use_stagnation_
        self._drawdown_threshold_, = self.MoneyManagement.DrawdownThreshold
        self._drawdown_factor_, = self.MoneyManagement.DrawdownFactor
        self._sizing_mode_ = SizingMode.parse(self.MoneyManagement.SizingMode[0])
        self._risk_percentage_, = self.MoneyManagement.RiskPercentage
        self._last_position_id_: Union[int, None] = None
        self._last_position_atr_: Union[float, None] = None
        self._last_position_trade_type_: Union[Direction, None] = None
        self._position_bars_held_: int = 0

    @staticmethod
    def _positive_(value: Union[float, None]) -> bool:
        return value is not None and value > 0.0

    def _risk_scale_(self, update: BarUpdateAPI) -> float:
        if self._drawdown_threshold_ <= 0.0: return 1.0
        drawdown = update.Portfolio.EquityDrawdown or 0.0
        return self._drawdown_factor_ if drawdown <= -self._drawdown_threshold_ / 100.0 else 1.0

    def define_so_buy_action(self, update: OpenedBuyPositionUpdateAPI) -> list:
        self._last_position_id_ = update.Position.UID
        self._position_bars_held_ = 0
        return [BidAboveTargetActionAPI(Bid=update.Position.EntryPrice.Price + self._scaling_out_scale_ * self._last_position_atr_)]

    def define_so_sell_action(self, update: OpenedSellPositionUpdateAPI) -> list:
        self._last_position_id_ = update.Position.UID
        self._position_bars_held_ = 0
        return [AskBelowTargetActionAPI(Ask=update.Position.EntryPrice.Price - self._scaling_out_scale_ * self._last_position_atr_)]

    def register_open_buy_action(self, update: OpenedBuyPositionUpdateAPI) -> list:
        self._last_position_id_ = update.Position.UID
        self._position_bars_held_ = 0
        return []

    def register_open_sell_action(self, update: OpenedSellPositionUpdateAPI) -> list:
        self._last_position_id_ = update.Position.UID
        self._position_bars_held_ = 0
        return []

    def define_tsl_open_buy_action(self, update: OpenedBuyPositionUpdateAPI) -> list:
        self._last_position_id_ = update.Position.UID
        self._position_bars_held_ = 0
        return [BidAboveTargetActionAPI(Bid=update.Position.StopLossPrice.Price + (self._trailing_stop_loss_scale_ + self._trailing_stop_loss_step_) * self._last_position_atr_ + update.Portfolio.Security.Contract.PointSize)]

    def define_tsl_open_sell_action(self, update: OpenedSellPositionUpdateAPI) -> list:
        self._last_position_id_ = update.Position.UID
        self._position_bars_held_ = 0
        return [AskBelowTargetActionAPI(Ask=update.Position.StopLossPrice.Price - (self._trailing_stop_loss_scale_ + self._trailing_stop_loss_step_) * self._last_position_atr_ - update.Portfolio.Security.Contract.PointSize)]

    def stagnation_stop_loss_action(self, update: BarUpdateAPI) -> list:
        self._position_bars_held_ += 1
        if self._position_bars_held_ < self._stagnation_stop_loss_: return []
        if update.Portfolio.BuyPositions: return self.close_buy_position(update)
        if update.Portfolio.SellPositions: return self.close_sell_position(update)
        return []

    def close_buy_partially_action(self, update: TickUpdateAPI) -> list:
        position = update.Portfolio.position(self._last_position_id_)
        volume = calculate_normalized_volume(position.Volume * (1.0 - self._scaling_out_percentage_ / 100), update.Portfolio.Security.Contract)
        if volume >= position.Volume: return [CloseBuyPositionActionAPI(PositionID=self._last_position_id_)]
        return [DecreaseBuyPositionVolumeActionAPI(PositionID=self._last_position_id_, Volume=volume)]

    def close_sell_partially_action(self, update: TickUpdateAPI) -> list:
        position = update.Portfolio.position(self._last_position_id_)
        volume = calculate_normalized_volume(position.Volume * (1.0 - self._scaling_out_percentage_ / 100), update.Portfolio.Security.Contract)
        if volume >= position.Volume: return [CloseSellPositionActionAPI(PositionID=self._last_position_id_)]
        return [DecreaseSellPositionVolumeActionAPI(PositionID=self._last_position_id_, Volume=volume)]

    def breakeven_buy_action(self, update: DecreasedBuyPositionVolumeUpdateAPI) -> list:
        return [ModifyBuyPositionStopLossActionAPI(PositionID=self._last_position_id_, StopLoss=update.Position.EntryPrice.Price)]

    def breakeven_sell_action(self, update: DecreasedSellPositionVolumeUpdateAPI) -> list:
        return [ModifySellPositionStopLossActionAPI(PositionID=self._last_position_id_, StopLoss=update.Position.EntryPrice.Price)]

    def define_tsl_buy_action(self, update: ModifiedBuyPositionStopLossUpdateAPI) -> list:
        return [BidAboveTargetActionAPI(Bid=update.Position.StopLossPrice.Price + (self._trailing_stop_loss_scale_ + self._trailing_stop_loss_step_) * self._last_position_atr_ + update.Portfolio.Security.Contract.PointSize)]

    def define_tsl_sell_action(self, update: ModifiedSellPositionStopLossUpdateAPI) -> list:
        return [AskBelowTargetActionAPI(Ask=update.Position.StopLossPrice.Price - (self._trailing_stop_loss_scale_ + self._trailing_stop_loss_step_) * self._last_position_atr_ - update.Portfolio.Security.Contract.PointSize)]

    def detected_tsl_buy_action(self, update: TickUpdateAPI) -> list:
        return [ModifyBuyPositionStopLossActionAPI(PositionID=self._last_position_id_, StopLoss=update.Tick.Bid.Price - self._trailing_stop_loss_scale_ * self._last_position_atr_)]

    def detected_tsl_sell_action(self, update: TickUpdateAPI) -> list:
        return [ModifySellPositionStopLossActionAPI(PositionID=self._last_position_id_, StopLoss=update.Tick.Ask.Price + self._trailing_stop_loss_scale_ * self._last_position_atr_)]

    @staticmethod
    def undefine_tsl_buy_action(_: Any) -> list:
        return [BidAboveTargetActionAPI(Bid=None)]

    @staticmethod
    def undefine_tsl_sell_action(_: Any) -> list:
        return [AskBelowTargetActionAPI(Ask=None)]

    def risk_management(self) -> MachineAPI:
        if not self._managed_risk_:
            unmanaged = MachineAPI(Name="Risk Management", Events=len(UpdateID))
            idle_initialization = unmanaged.state(name="Initialization")
            idle_waiting = unmanaged.state(name="No Position")
            idle_termination = unmanaged.state(name="Termination", end=True)
            idle_initialization.on(event=UpdateID.Execution, to=idle_waiting, action=None, reason="Initialized")
            idle_initialization.on(event=UpdateID.Shutdown, to=idle_termination, action=None, reason="Abruptly Terminated")
            idle_waiting.on(event=UpdateID.OpenedBuyPosition, to=idle_waiting, action=self.register_open_buy_action, reason="Opened Buy Position")
            idle_waiting.on(event=UpdateID.OpenedSellPosition, to=idle_waiting, action=self.register_open_sell_action, reason="Opened Sell Position")
            idle_waiting.on(event=UpdateID.Shutdown, to=idle_termination, action=None, reason="Safely Terminated")
            return unmanaged
        risk_engine = MachineAPI(Name="Risk Management", Events=len(UpdateID))

        initialization = risk_engine.state(name="Initialization")
        waiting_open = risk_engine.state(name="No Position")
        waiting_so = risk_engine.state(name="Waiting SO")
        waiting_tsl = risk_engine.state(name="Waiting TSL")
        waiting_close = risk_engine.state(name="Waiting Close")
        termination = risk_engine.state(name="Termination", end=True)

        initialization.on(event=UpdateID.Execution, to=waiting_open, action=None, reason="Initialized")
        initialization.on(event=UpdateID.Shutdown, to=termination, action=None, reason="Abruptly Terminated")

        waiting_open.on(event=UpdateID.OpenedBuyPosition, to=waiting_so, action=self.define_so_buy_action, reason="Opened Buy Position")
        waiting_open.on(event=UpdateID.OpenedSellPosition, to=waiting_so, action=self.define_so_sell_action, reason="Opened Sell Position")
        waiting_open.on(event=UpdateID.Shutdown, to=termination, action=None, reason="Safely Terminated")

        waiting_so.on(event=UpdateID.ClosedBuyPosition, to=waiting_open, action=self.undefine_tsl_buy_action, reason="Closed Buy Position")
        waiting_so.on(event=UpdateID.StopLossBuyPosition, to=waiting_open, action=self.undefine_tsl_buy_action, reason="Stop-Loss Hit on Buy Position")
        waiting_so.on(event=UpdateID.TakeProfitBuyPosition, to=waiting_open, action=self.undefine_tsl_buy_action, reason="Take-Profit Hit on Buy Position")
        waiting_so.on(event=UpdateID.MarginCallBuyPosition, to=waiting_open, action=self.undefine_tsl_buy_action, reason="Margin Call on Buy Position")
        waiting_so.on(event=UpdateID.ClosedSellPosition, to=waiting_open, action=self.undefine_tsl_sell_action, reason="Closed Sell Position")
        waiting_so.on(event=UpdateID.StopLossSellPosition, to=waiting_open, action=self.undefine_tsl_sell_action, reason="Stop-Loss Hit on Sell Position")
        waiting_so.on(event=UpdateID.TakeProfitSellPosition, to=waiting_open, action=self.undefine_tsl_sell_action, reason="Take-Profit Hit on Sell Position")
        waiting_so.on(event=UpdateID.MarginCallSellPosition, to=waiting_open, action=self.undefine_tsl_sell_action, reason="Margin Call on Sell Position")
        waiting_so.on(event=UpdateID.BidAboveTarget, to=waiting_so, action=self.close_buy_partially_action, reason="Hit SO Activation for Buy Position")
        waiting_so.on(event=UpdateID.AskBelowTarget, to=waiting_so, action=self.close_sell_partially_action, reason="Hit SO Activation for Sell Position")
        waiting_so.on(event=UpdateID.DecreasedBuyPositionVolume, to=waiting_so, action=self.breakeven_buy_action, reason="Closed Partially Buy Position")
        waiting_so.on(event=UpdateID.DecreasedSellPositionVolume, to=waiting_so, action=self.breakeven_sell_action, reason="Closed Partially Sell Position")
        waiting_so.on(event=UpdateID.ModifiedBuyPositionStopLoss, to=waiting_tsl, action=self.define_tsl_buy_action, reason="Moved Buy Position to Break-Even")
        waiting_so.on(event=UpdateID.ModifiedSellPositionStopLoss, to=waiting_tsl, action=self.define_tsl_sell_action, reason="Moved Sell Position to Break-Even")
        waiting_so.on(event=UpdateID.Shutdown, to=termination, action=None, reason="Safely Terminated")

        waiting_tsl.on(event=UpdateID.ClosedBuyPosition, to=waiting_open, action=self.undefine_tsl_buy_action, reason="Closed Buy Position")
        waiting_tsl.on(event=UpdateID.StopLossBuyPosition, to=waiting_open, action=self.undefine_tsl_buy_action, reason="Stop-Loss Hit on Buy Position")
        waiting_tsl.on(event=UpdateID.TakeProfitBuyPosition, to=waiting_open, action=self.undefine_tsl_buy_action, reason="Take-Profit Hit on Buy Position")
        waiting_tsl.on(event=UpdateID.MarginCallBuyPosition, to=waiting_open, action=self.undefine_tsl_buy_action, reason="Margin Call on Buy Position")
        waiting_tsl.on(event=UpdateID.ClosedSellPosition, to=waiting_open, action=self.undefine_tsl_sell_action, reason="Closed Sell Position")
        waiting_tsl.on(event=UpdateID.StopLossSellPosition, to=waiting_open, action=self.undefine_tsl_sell_action, reason="Stop-Loss Hit on Sell Position")
        waiting_tsl.on(event=UpdateID.TakeProfitSellPosition, to=waiting_open, action=self.undefine_tsl_sell_action, reason="Take-Profit Hit on Sell Position")
        waiting_tsl.on(event=UpdateID.MarginCallSellPosition, to=waiting_open, action=self.undefine_tsl_sell_action, reason="Margin Call on Sell Position")
        waiting_tsl.on(event=UpdateID.BidAboveTarget, to=waiting_tsl, action=self.detected_tsl_buy_action, reason="Hit TSL Activation for Buy Position")
        waiting_tsl.on(event=UpdateID.AskBelowTarget, to=waiting_tsl, action=self.detected_tsl_sell_action, reason="Hit TSL Activation for Sell Position")
        waiting_tsl.on(event=UpdateID.ModifiedBuyPositionStopLoss, to=waiting_close, action=self.define_tsl_buy_action, reason="Activated TSL for Buy Position")
        waiting_tsl.on(event=UpdateID.ModifiedSellPositionStopLoss, to=waiting_close, action=self.define_tsl_sell_action, reason="Activated TSL for Sell Position")
        waiting_tsl.on(event=UpdateID.Shutdown, to=termination, action=None, reason="Safely Terminated")

        waiting_close.on(event=UpdateID.ClosedBuyPosition, to=waiting_open, action=self.undefine_tsl_buy_action, reason="Closed Buy Position")
        waiting_close.on(event=UpdateID.StopLossBuyPosition, to=waiting_open, action=self.undefine_tsl_buy_action, reason="Stop-Loss Hit on Buy Position")
        waiting_close.on(event=UpdateID.TakeProfitBuyPosition, to=waiting_open, action=self.undefine_tsl_buy_action, reason="Take-Profit Hit on Buy Position")
        waiting_close.on(event=UpdateID.MarginCallBuyPosition, to=waiting_open, action=self.undefine_tsl_buy_action, reason="Margin Call on Buy Position")
        waiting_close.on(event=UpdateID.ClosedSellPosition, to=waiting_open, action=self.undefine_tsl_sell_action, reason="Closed Sell Position")
        waiting_close.on(event=UpdateID.StopLossSellPosition, to=waiting_open, action=self.undefine_tsl_sell_action, reason="Stop-Loss Hit on Sell Position")
        waiting_close.on(event=UpdateID.TakeProfitSellPosition, to=waiting_open, action=self.undefine_tsl_sell_action, reason="Take-Profit Hit on Sell Position")
        waiting_close.on(event=UpdateID.MarginCallSellPosition, to=waiting_open, action=self.undefine_tsl_sell_action, reason="Margin Call on Sell Position")
        waiting_close.on(event=UpdateID.BidAboveTarget, to=waiting_close, action=self.detected_tsl_buy_action, reason="Hit TSL Update for Buy Position")
        waiting_close.on(event=UpdateID.AskBelowTarget, to=waiting_close, action=self.detected_tsl_sell_action, reason="Hit TSL Update for Sell Position")
        waiting_close.on(event=UpdateID.ModifiedBuyPositionStopLoss, to=waiting_close, action=self.define_tsl_buy_action, reason="Updated TSL for Buy Position")
        waiting_close.on(event=UpdateID.ModifiedSellPositionStopLoss, to=waiting_close, action=self.define_tsl_sell_action, reason="Updated TSL for Sell Position")
        waiting_close.on(event=UpdateID.Shutdown, to=termination, action=None, reason="Safely Terminated")

        if not self._use_scaling_out_:
            if self._use_trailing_stop_loss_:
                waiting_open.on(event=UpdateID.OpenedBuyPosition, to=waiting_tsl, action=self.define_tsl_open_buy_action, reason="Opened Buy Position")
                waiting_open.on(event=UpdateID.OpenedSellPosition, to=waiting_tsl, action=self.define_tsl_open_sell_action, reason="Opened Sell Position")
            else:
                waiting_open.on(event=UpdateID.OpenedBuyPosition, to=waiting_close, action=self.register_open_buy_action, reason="Opened Buy Position")
                waiting_open.on(event=UpdateID.OpenedSellPosition, to=waiting_close, action=self.register_open_sell_action, reason="Opened Sell Position")
        if not self._use_trailing_stop_loss_:
            waiting_so.on(event=UpdateID.ModifiedBuyPositionStopLoss, to=waiting_close, action=None, reason="Moved Buy Position to Break-Even")
            waiting_so.on(event=UpdateID.ModifiedSellPositionStopLoss, to=waiting_close, action=None, reason="Moved Sell Position to Break-Even")
        if self._use_stagnation_:
            waiting_so.on(event=UpdateID.BarClosed, to=waiting_so, action=self.stagnation_stop_loss_action, reason=None)
            if not self._use_scaling_out_:
                if self._use_trailing_stop_loss_:
                    waiting_tsl.on(event=UpdateID.BarClosed, to=waiting_tsl, action=self.stagnation_stop_loss_action, reason=None)
                else:
                    waiting_close.on(event=UpdateID.BarClosed, to=waiting_close, action=self.stagnation_stop_loss_action, reason=None)

        return risk_engine

    def calculate_position(self, update: BarUpdateAPI) -> tuple:
        self._last_position_atr_ = update.Technical.ATR.Result.last()
        pip_size = update.Portfolio.Security.Contract.PipSize
        sl_pips = self._stop_loss_scale_ * self._last_position_atr_ / pip_size if self._use_stop_loss_ else 0.0
        sizing_pips = self._sizing_atr_scale_ * self._last_position_atr_ / pip_size
        size = self._risk_percentage_ * self._risk_scale_(update)
        contract = update.Portfolio.Security.Contract
        if self._sizing_mode_ == SizingMode.Volume:
            volume = calculate_normalized_volume(size, contract)
        elif self._sizing_mode_ == SizingMode.Balance:
            account = update.Portfolio.Account
            price = update.Bar.CloseTick.Bid.Price
            volume = calculate_normalized_volume(account.Balance * (size / 100.0) / price, contract) if account and account.Balance and price else 0.0
        else:
            volume = calculate_fixed_fractional_volume(size, sizing_pips, update.Portfolio.Account, contract)
        return volume, sl_pips

    def open_buy_position(self, update: BarUpdateAPI, position_type: PositionType) -> list:
        self._last_position_trade_type_ = Direction.Buy
        volume, sl_pips = self.calculate_position(update)
        return self.close_sell_position(update) + [OpenBuyPositionActionAPI(PositionType=position_type, Volume=volume, StopLoss=sl_pips if self._use_stop_loss_ else None, TakeProfit=None)]

    def open_sell_position(self, update: BarUpdateAPI, position_type: PositionType) -> list:
        self._last_position_trade_type_ = Direction.Sell
        volume, sl_pips = self.calculate_position(update)
        return self.close_buy_position(update) + [OpenSellPositionActionAPI(PositionType=position_type, Volume=volume, StopLoss=sl_pips if self._use_stop_loss_ else None, TakeProfit=None)]

    def close_buy_position(self, update: BarUpdateAPI) -> list:
        return [CloseBuyPositionActionAPI(PositionID=self._last_position_id_)] if update.Portfolio.BuyPositions else []

    def close_sell_position(self, update: BarUpdateAPI) -> list:
        return [CloseSellPositionActionAPI(PositionID=self._last_position_id_)] if update.Portfolio.SellPositions else []

    def signal_management(self) -> None:
        return None