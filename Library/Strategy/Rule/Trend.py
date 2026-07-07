from __future__ import annotations

from typing import Union, TYPE_CHECKING

from Library.Engine import MachineAPI
from Library.Indicator.Indicator import IndicatorMode
from Library.Market.Price import Direction
from Library.Portfolio import PositionType
from Library.Protocol.Update import UpdateID, BarUpdateAPI
from Library.Strategy.Rule.NNFX import NNFXStrategyAPI

if TYPE_CHECKING:
    from Library.Parameter import Parameter

class TrendStrategyAPI(NNFXStrategyAPI):

    def __init__(self,
                 money_management: Parameter,
                 risk_management: Parameter,
                 signal_management: Parameter,
                 technical_management: Parameter,
                 fundamental_management: Parameter,
                 sentimental_management: Parameter,
                 portfolio_management: Parameter) -> None:
        super().__init__(money_management, risk_management, signal_management, technical_management, fundamental_management, sentimental_management, portfolio_management)
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

    def update_position(self, update: BarUpdateAPI) -> Union[list, None]:
        if not update.Portfolio.BuyPositions and self._normal_entry_buy_(update):
            return self.open_buy_position(update, PositionType.Normal)
        if not update.Portfolio.SellPositions and self._normal_entry_sell_(update):
            return self.open_sell_position(update, PositionType.Normal)
        if update.Portfolio.BuyPositions and self._normal_exit_buy_(update):
            return self.close_buy_position(update)
        if update.Portfolio.SellPositions and self._normal_exit_sell_(update):
            return self.close_sell_position(update)
        if not update.Portfolio.BuyPositions and self._last_position_trade_type_ == Direction.Buy and self._continuation_entry_buy_(update):
            return self.open_buy_position(update, PositionType.Continuation)
        if not update.Portfolio.SellPositions and self._last_position_trade_type_ == Direction.Sell and self._continuation_entry_sell_(update):
            return self.open_sell_position(update, PositionType.Continuation)
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