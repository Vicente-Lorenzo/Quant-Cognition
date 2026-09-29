from __future__ import annotations

from typing import ClassVar, Any, Callable, Union, TYPE_CHECKING

from Library.Market.Price import Direction
from Library.Portfolio.Position import PositionAPI, PositionType
from Library.Portfolio.Sizing import calculate_normalized_volume
from Library.Protocol.Action import (
    AskBelowTargetActionAPI,
    BidAboveTargetActionAPI,
    CloseBuyPositionActionAPI,
    CloseSellPositionActionAPI,
    IncreaseBuyPositionVolumeActionAPI,
    IncreaseSellPositionVolumeActionAPI,
    ModifyBuyPositionVolumeActionAPI,
    ModifySellPositionVolumeActionAPI,
    ModifyBuyPositionTakeProfitActionAPI,
    ModifySellPositionTakeProfitActionAPI,
    OpenBuyPositionActionAPI,
    OpenSellPositionActionAPI
)
from Library.Protocol.Update import BarUpdateAPI, TickUpdateAPI, DecreasedBuyPositionVolumeUpdateAPI, DecreasedSellPositionVolumeUpdateAPI
from Library.Strategy.Rule.Trend import TrendStrategyAPI
from Library.Utility.Enumeration import EnumerationAPI

if TYPE_CHECKING:
    from Library.Utility.Parameter import Parameter

class ScenarioType(EnumerationAPI):

    Plain = 0
    Target = 1
    Resize = 2
    Hedge = 3

class TestStrategyAPI(TrendStrategyAPI):

    Defaults: ClassVar[dict] = {
        "Realtime": {
            'FundamentalManagement': None,
            'MoneyManagement': {
                'DrawdownFactor': [1.0],
                'DrawdownThreshold': [0.0],
                'RiskPercentage': [1.0],
                'SizingMode': ['Risk'],
            },
            'PortfolioManagement': None,
            'RiskManagement': {
                'ScalingOutPercentage': [50.0],
                'ScalingOutScale': [1.0],
                'StagnationStopLoss': [0],
                'StopLossScale': [1.5],
                'TakeProfitScale': [3.0],
                'TrailingStopLossScale': [1.5],
                'TrailingStopLossStep': [0.25],
            },
            'SentimentalManagement': None,
            'SignalManagement': {
                'BaselineMode': ['Signal', False, 'Signal'],
                'DirectionalEntryThreshold': None,
                'DirectionalExitThreshold': None,
                'Filter1Mode': ['Filter', False, False],
                'Filter2Mode': ['Filter', False, False],
                'VolumeEntryThreshold': None,
                'VolumeExitThreshold': None,
                'VolumeMode': ['Filter', False, False],
            },
            'TechnicalManagement': {
                'ATR': ['ATR', 14],
                'Baseline': ['SMA', 20],
                'Filter1': ['TT'],
                'Filter2': ['TT'],
                'Volume': ['TT'],
            },
        },
        "Optimization": {
            'FundamentalManagement': None,
            'MoneyManagement': {
                'RiskPercentage': [[0.5, 1.0]],
            },
            'PortfolioManagement': None,
            'RiskManagement': {
                'TakeProfitScale': [[2.0, 3.0]],
            },
            'SentimentalManagement': None,
            'SignalManagement': None,
            'TechnicalManagement': {
                'Baseline': [['SMA', 'EMA'], [10, 20]],
            },
        },
    }

    def __init__(self,
                 money_management: Parameter,
                 risk_management: Parameter,
                 signal_management: Parameter,
                 technical_management: Parameter,
                 fundamental_management: Parameter,
                 sentimental_management: Parameter,
                 portfolio_management: Parameter) -> None:
        super().__init__(money_management, risk_management, signal_management, technical_management, fundamental_management, sentimental_management, portfolio_management)
        self._take_profit_scale_, = self.RiskManagement.TakeProfitScale
        self._entries_: dict[Direction, int] = {Direction.Buy: 0, Direction.Sell: 0}
        self._scenario_: ScenarioType = ScenarioType.Plain
        self._direction_: Union[Direction, None] = None
        self._volume_: float = 0.0
        self._steps_: list[Callable] = []

    @staticmethod
    def _side_(update: BarUpdateAPI, direction: Direction) -> list:
        return update.Portfolio.BuyPositions if direction == Direction.Buy else update.Portfolio.SellPositions

    def _primary_(self, update: BarUpdateAPI) -> Union[PositionAPI, None]:
        positions = self._side_(update, self._direction_)
        return min(positions, key=lambda position: position.UID) if positions else None

    def _half_(self, update: BarUpdateAPI) -> float:
        return calculate_normalized_volume(self._volume_ / 2.0, update.Portfolio.Security.Contract)

    def _distances_(self, update: BarUpdateAPI) -> tuple[float, float]:
        pips = self._last_position_atr_ / update.Portfolio.Security.Contract.PipSize
        return self._stop_loss_scale_ * pips, self._take_profit_scale_ * pips

    def _open_(self, direction: Direction, update: BarUpdateAPI) -> list:
        stop, target = self._distances_(update)
        action = OpenBuyPositionActionAPI if direction == Direction.Buy else OpenSellPositionActionAPI
        return [action(PositionType=PositionType.Continuation, Volume=self._half_(update), StopLoss=stop, TakeProfit=target)]

    @staticmethod
    def _reached_(position: Union[PositionAPI, None], bid: float, ask: float) -> bool:
        if position is None or position.TakeProfitPrice is None: return False
        return bid >= position.TakeProfitPrice.Price if position.Direction == Direction.Buy else ask <= position.TakeProfitPrice.Price

    def _widen_target_(self, update: BarUpdateAPI, primary: PositionAPI) -> list:
        if primary.TakeProfitPrice is None or self._reached_(primary, update.Bar.ClosePoint.Bid.Price, update.Bar.ClosePoint.Ask.Price): return []
        if self._direction_ == Direction.Buy: return [ModifyBuyPositionTakeProfitActionAPI(PositionID=primary.UID, TakeProfit=primary.TakeProfitPrice.Price + self._last_position_atr_)]
        return [ModifySellPositionTakeProfitActionAPI(PositionID=primary.UID, TakeProfit=primary.TakeProfitPrice.Price - self._last_position_atr_)]

    def _increase_volume_(self, update: BarUpdateAPI, primary: PositionAPI) -> list:
        volume = min(primary.Volume + self._half_(update), update.Portfolio.Security.Contract.VolumeMax)
        if self._direction_ == Direction.Buy: return [IncreaseBuyPositionVolumeActionAPI(PositionID=primary.UID, Volume=volume)]
        return [IncreaseSellPositionVolumeActionAPI(PositionID=primary.UID, Volume=volume)]

    def _modify_volume_(self, update: BarUpdateAPI, primary: PositionAPI) -> list:
        volume = min(primary.Volume + self._half_(update), update.Portfolio.Security.Contract.VolumeMax)
        if self._direction_ == Direction.Buy: return [ModifyBuyPositionVolumeActionAPI(PositionID=primary.UID, Volume=volume)]
        return [ModifySellPositionVolumeActionAPI(PositionID=primary.UID, Volume=volume)]

    def _add_same_(self, update: BarUpdateAPI, _: PositionAPI) -> list:
        return self._open_(self._direction_, update)

    def _add_opposite_(self, update: BarUpdateAPI, _: PositionAPI) -> list:
        return self._open_(Direction.Sell if self._direction_ == Direction.Buy else Direction.Buy, update)

    def _close_opposite_(self, update: BarUpdateAPI, _: PositionAPI) -> list:
        return self.close_sell_position(update) if self._direction_ == Direction.Buy else self.close_buy_position(update)

    def _rotate_(self, update: BarUpdateAPI, actions: list, direction: Direction) -> list:
        self._scenario_ = ScenarioType(self._entries_[direction] % len(ScenarioType))
        self._entries_[direction] += 1
        self._direction_, self._volume_ = direction, actions[-1].Volume
        match self._scenario_:
            case ScenarioType.Target:
                actions[-1].TakeProfit = self._distances_(update)[1]
                self._steps_ = [self._widen_target_]
            case ScenarioType.Resize: self._steps_ = [self._increase_volume_, self._modify_volume_]
            case ScenarioType.Hedge: self._steps_ = [self._add_same_, self._add_opposite_, self._close_opposite_]
            case _: self._steps_ = []
        return actions

    def _follow_(self, update: BarUpdateAPI) -> Union[list, None]:
        primary = self._primary_(update)
        if primary is None:
            self._steps_ = []
            return None
        return self._steps_.pop(0)(update, primary)

    def update_position(self, update: BarUpdateAPI) -> Union[list, None]:
        actions = self._signal_position_(update)
        if actions is None and self._steps_: actions = self._follow_(update)
        return self._emit_(update, actions)

    def detected_tsl_buy_action(self, update: TickUpdateAPI) -> list:
        if self._reached_(update.Portfolio.position(self._last_position_id_), update.Tick.Bid.Price, update.Tick.Ask.Price): return []
        return super().detected_tsl_buy_action(update)

    def detected_tsl_sell_action(self, update: TickUpdateAPI) -> list:
        if self._reached_(update.Portfolio.position(self._last_position_id_), update.Tick.Bid.Price, update.Tick.Ask.Price): return []
        return super().detected_tsl_sell_action(update)

    def breakeven_buy_action(self, update: DecreasedBuyPositionVolumeUpdateAPI) -> list:
        if update.Trade.ExitPrice.Price <= update.Position.EntryPrice.Price: return []
        return super().breakeven_buy_action(update)

    def breakeven_sell_action(self, update: DecreasedSellPositionVolumeUpdateAPI) -> list:
        if update.Trade.ExitPrice.Price >= update.Position.EntryPrice.Price: return []
        return super().breakeven_sell_action(update)

    @staticmethod
    def undefine_tsl_buy_action(_: Any) -> list:
        return [BidAboveTargetActionAPI(Bid=None), AskBelowTargetActionAPI(Ask=None)]

    @staticmethod
    def undefine_tsl_sell_action(_: Any) -> list:
        return [BidAboveTargetActionAPI(Bid=None), AskBelowTargetActionAPI(Ask=None)]

    def open_buy_position(self, update: BarUpdateAPI, position_type: PositionType) -> list:
        return self._rotate_(update, super().open_buy_position(update, position_type), Direction.Buy)

    def open_sell_position(self, update: BarUpdateAPI, position_type: PositionType) -> list:
        return self._rotate_(update, super().open_sell_position(update, position_type), Direction.Sell)

    def close_buy_position(self, update: BarUpdateAPI) -> list:
        return [CloseBuyPositionActionAPI(PositionID=position.UID) for position in update.Portfolio.BuyPositions]

    def close_sell_position(self, update: BarUpdateAPI) -> list:
        return [CloseSellPositionActionAPI(PositionID=position.UID) for position in update.Portfolio.SellPositions]