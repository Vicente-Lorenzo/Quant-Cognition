from __future__ import annotations

from typing import Any, Union, TYPE_CHECKING

from Library.Engine import MachineAPI
from Library.Indicator.Indicator import IndicatorMode
from Library.Market.Price import Direction
from Library.Portfolio import PositionType
from Library.Portfolio.Sizing import calculate_fixed_fractional_volume
from Library.Protocol.Action import (
    AskBelowTargetActionAPI,
    BidAboveTargetActionAPI,
    CloseBuyPositionActionAPI,
    CloseSellPositionActionAPI,
    ModifyBuyPositionStopLossActionAPI,
    ModifyBuyPositionVolumeActionAPI,
    ModifySellPositionStopLossActionAPI,
    ModifySellPositionVolumeActionAPI,
    OpenBuyPositionActionAPI,
    OpenSellPositionActionAPI
)
from Library.Protocol.Update import (
    UpdateID,
    BarUpdateAPI,
    TickUpdateAPI,
    OpenedBuyPositionUpdateAPI,
    OpenedSellPositionUpdateAPI,
    ModifiedBuyPositionVolumeUpdateAPI,
    ModifiedSellPositionVolumeUpdateAPI,
    ModifiedBuyPositionStopLossUpdateAPI,
    ModifiedSellPositionStopLossUpdateAPI
)
from Library.Strategy.Strategy import StrategyAPI

if TYPE_CHECKING:
    from Library.Parameters import Parameters

class NNFXStrategyAPI(StrategyAPI):

    def __init__(self,
                 money_management: Parameters,
                 risk_management: Parameters,
                 signal_management: Parameters) -> None:
        super().__init__(money_management, risk_management, signal_management)

        self._risk_percentage_, = self.MoneyManagement.RiskPercentage
        self._stop_loss_scale_, = self.RiskManagement.StopLossScale
        self._scaling_out_scale_, = self.RiskManagement.ScalingOutScale
        self._scaling_out_percentage_, = self.RiskManagement.ScalingOutPercentage
        self._trailing_stop_loss_scale_, = self.RiskManagement.TrailingStopLossScale

        modes = {
            "Baseline": self.SignalManagement.BaselineMode,
            "Filter1": self.SignalManagement.Filter1Mode,
            "Filter2": self.SignalManagement.Filter2Mode,
            "Volume": self.SignalManagement.VolumeMode
        }

        normal_entries_buy = []
        normal_entries_sell = []
        continuation_entries_buy = []
        continuation_entries_sell = []
        normal_exits_buy = []
        normal_exits_sell = []

        for technical_name, (normal_entry_mode, continuation_entry_mode, normal_exit_mode) in modes.items():
            match normal_entry_mode:
                case IndicatorMode.Filter.name:
                    normal_entries_buy.append(lambda update, tname=technical_name: getattr(update.Technical, tname).filter_buy(update.Market))
                    normal_entries_sell.append(lambda update, tname=technical_name: getattr(update.Technical, tname).filter_sell(update.Market))
                case IndicatorMode.Signal.name:
                    normal_entries_buy.append(lambda update, tname=technical_name: getattr(update.Technical, tname).signal_buy(update.Market))
                    normal_entries_sell.append(lambda update, tname=technical_name: getattr(update.Technical, tname).signal_sell(update.Market))
            match continuation_entry_mode:
                case IndicatorMode.Filter.name:
                    continuation_entries_buy.append(lambda update, tname=technical_name: getattr(update.Technical, tname).filter_buy(update.Market))
                    continuation_entries_sell.append(lambda update, tname=technical_name: getattr(update.Technical, tname).filter_sell(update.Market))
                case IndicatorMode.Signal.name:
                    continuation_entries_buy.append(lambda update, tname=technical_name: getattr(update.Technical, tname).signal_buy(update.Market))
                    continuation_entries_sell.append(lambda update, tname=technical_name: getattr(update.Technical, tname).signal_sell(update.Market))
            match normal_exit_mode:
                case IndicatorMode.Filter.name:
                    normal_exits_buy.append(lambda update, tname=technical_name: getattr(update.Technical, tname).filter_sell(update.Market))
                    normal_exits_sell.append(lambda update, tname=technical_name: getattr(update.Technical, tname).filter_buy(update.Market))
                case IndicatorMode.Signal.name:
                    normal_exits_buy.append(lambda update, tname=technical_name: getattr(update.Technical, tname).signal_sell(update.Market))
                    normal_exits_sell.append(lambda update, tname=technical_name: getattr(update.Technical, tname).signal_buy(update.Market))

        self._normal_entry_buy_ = lambda update: all(f(update) for f in normal_entries_buy) if normal_entries_buy else False
        self._normal_entry_sell_ = lambda update: all(f(update) for f in normal_entries_sell) if normal_entries_sell else False
        self._continuation_entry_buy_ = lambda update: all(f(update) for f in continuation_entries_buy) if continuation_entries_buy else False
        self._continuation_entry_sell_ = lambda update: all(f(update) for f in continuation_entries_sell) if continuation_entries_sell else False
        self._normal_exit_buy_ = lambda update: any(f(update) for f in normal_exits_buy) if normal_exits_buy else False
        self._normal_exit_sell_ = lambda update: any(f(update) for f in normal_exits_sell) if normal_exits_sell else False

        self._last_position_id_: Union[int, None] = None
        self._last_position_atr_: Union[float, None] = None
        self._last_position_trade_type_: Union[Direction, None] = None

    def define_so_buy_action(self, update: OpenedBuyPositionUpdateAPI) -> list:
        self._last_position_id_ = update.Position.UID
        return [BidAboveTargetActionAPI(Bid=update.Position.EntryPrice.Price + self._scaling_out_scale_ * self._last_position_atr_)]

    def define_so_sell_action(self, update: OpenedSellPositionUpdateAPI) -> list:
        self._last_position_id_ = update.Position.UID
        return [AskBelowTargetActionAPI(Ask=update.Position.EntryPrice.Price - self._scaling_out_scale_ * self._last_position_atr_)]

    def close_buy_partially_action(self, update: TickUpdateAPI) -> list:
        position = update.Portfolio.position(self._last_position_id_)
        volume = position.Volume * (1.0 - self._scaling_out_percentage_ / 100)
        return [ModifyBuyPositionVolumeActionAPI(PositionID=self._last_position_id_, Volume=volume)]

    def close_sell_partially_action(self, update: TickUpdateAPI) -> list:
        position = update.Portfolio.position(self._last_position_id_)
        volume = position.Volume * (1.0 - self._scaling_out_percentage_ / 100)
        return [ModifySellPositionVolumeActionAPI(PositionID=self._last_position_id_, Volume=volume)]

    def breakeven_buy_action(self, update: ModifiedBuyPositionVolumeUpdateAPI) -> list:
        return [ModifyBuyPositionStopLossActionAPI(PositionID=self._last_position_id_, StopLoss=update.Position.EntryPrice.Price)]

    def breakeven_sell_action(self, update: ModifiedSellPositionVolumeUpdateAPI) -> list:
        return [ModifySellPositionStopLossActionAPI(PositionID=self._last_position_id_, StopLoss=update.Position.EntryPrice.Price)]

    def define_tsl_buy_action(self, update: ModifiedBuyPositionStopLossUpdateAPI) -> list:
        return [BidAboveTargetActionAPI(Bid=update.Position.StopLossPrice.Price + self._trailing_stop_loss_scale_ * self._last_position_atr_ + update.Portfolio.Security.Contract.PointSize)]

    def define_tsl_sell_action(self, update: ModifiedSellPositionStopLossUpdateAPI) -> list:
        return [AskBelowTargetActionAPI(Ask=update.Position.StopLossPrice.Price - self._trailing_stop_loss_scale_ * self._last_position_atr_ - update.Portfolio.Security.Contract.PointSize)]

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
        risk_engine = MachineAPI(Name="Risk Management", Events=len(UpdateID))

        initialisation = risk_engine.state(name="Initialisation")
        waiting_open = risk_engine.state(name="No Position")
        waiting_so = risk_engine.state(name="Waiting SO")
        waiting_tsl = risk_engine.state(name="Waiting TSL")
        waiting_close = risk_engine.state(name="Waiting Close")
        termination = risk_engine.state(name="Termination", end=True)

        initialisation.on(event=UpdateID.Complete, to=waiting_open, action=None, reason="Initialized")
        initialisation.on(event=UpdateID.Shutdown, to=termination, action=None, reason="Abruptly Terminated")

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
        waiting_so.on(event=UpdateID.ModifiedBuyPositionVolume, to=waiting_so, action=self.breakeven_buy_action, reason="Closed Partially Buy Position")
        waiting_so.on(event=UpdateID.ModifiedSellPositionVolume, to=waiting_so, action=self.breakeven_sell_action, reason="Closed Partially Sell Position")
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

        return risk_engine

    def calculate_position(self, update: BarUpdateAPI) -> tuple:
        self._last_position_atr_ = update.Technical.Volatility.Result.last()
        sl_pips = self._stop_loss_scale_ * self._last_position_atr_ / update.Portfolio.Security.Contract.PipSize
        volume = calculate_fixed_fractional_volume(self._risk_percentage_, sl_pips, update.Portfolio.Account, update.Portfolio.Security.Contract)
        return volume, sl_pips

    def open_buy_position(self, update: BarUpdateAPI, position_type: PositionType) -> list:
        self._last_position_trade_type_ = Direction.Buy
        volume, sl_pips = self.calculate_position(update)
        return self.close_sell_position(update) + [OpenBuyPositionActionAPI(PositionType=position_type, Volume=volume, StopLoss=sl_pips, TakeProfit=None)]

    def open_sell_position(self, update: BarUpdateAPI, position_type: PositionType) -> list:
        self._last_position_trade_type_ = Direction.Sell
        volume, sl_pips = self.calculate_position(update)
        return self.close_buy_position(update) + [OpenSellPositionActionAPI(PositionType=position_type, Volume=volume, StopLoss=sl_pips, TakeProfit=None)]

    def close_buy_position(self, update: BarUpdateAPI) -> list:
        return [CloseBuyPositionActionAPI(PositionID=self._last_position_id_)] if update.Portfolio.BuyPositions else []

    def close_sell_position(self, update: BarUpdateAPI) -> list:
        return [CloseSellPositionActionAPI(PositionID=self._last_position_id_)] if update.Portfolio.SellPositions else []

    def update_position(self, update: BarUpdateAPI) -> Union[list, None]:
        if not update.Portfolio.BuyPositions:
            if self._normal_entry_buy_(update):
                return self.open_buy_position(update, PositionType.Normal)
            if self._last_position_trade_type_ and self._last_position_trade_type_ == Direction.Buy and self._continuation_entry_buy_(update):
                return self.open_buy_position(update, PositionType.Continuation)
        elif self._normal_exit_buy_(update):
            return self.close_buy_position(update)

        if not update.Portfolio.SellPositions:
            if self._normal_entry_sell_(update):
                return self.open_sell_position(update, PositionType.Normal)
            if self._last_position_trade_type_ and self._last_position_trade_type_ == Direction.Sell and self._continuation_entry_sell_(update):
                return self.open_sell_position(update, PositionType.Continuation)
        elif self._normal_exit_sell_(update):
            return self.close_sell_position(update)
        return None

    def signal_management(self) -> MachineAPI:
        signal_engine = MachineAPI(Name="Signal Management", Events=len(UpdateID))

        initialisation = signal_engine.state(name="Initialisation")
        waiting_signal = signal_engine.state(name="Waiting Signal")
        termination = signal_engine.state(name="Termination", end=True)

        initialisation.on(event=UpdateID.Complete, to=waiting_signal, action=None, reason="Initialized")
        initialisation.on(event=UpdateID.Shutdown, to=termination, action=None, reason="Abruptly Terminated")

        waiting_signal.on(event=UpdateID.BarClosed, to=waiting_signal, action=self.update_position, reason=None)
        waiting_signal.on(event=UpdateID.Shutdown, to=termination, action=None, reason="Safely Terminated")

        return signal_engine