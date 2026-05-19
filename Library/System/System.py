from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Type, Union, TYPE_CHECKING
from typing_extensions import Self

from Library.Database.Enumeration import EnumerationAPI
from Library.Logging import HandlerLoggingAPI
from Library.Portfolio.Order import OrderAPI
from Library.Portfolio.Position import PositionAPI
from Library.Portfolio.Trade import TradeAPI
from Library.System.Buffer import BufferAPI
from Library.Protocol.Action import ActionAPI, ActionID, CompleteActionAPI
from Library.Protocol.Update import (
    UpdateID,
    CompleteUpdateAPI,
    AccountUpdateAPI,
    SecurityUpdateAPI,
    BarUpdateAPI,
    TickUpdateAPI,
    OpenedBuyPositionUpdateAPI,
    OpenedSellPositionUpdateAPI,
    ModifiedBuyPositionVolumeUpdateAPI,
    ModifiedSellPositionVolumeUpdateAPI,
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
    OpenedBuyStopOrderUpdateAPI,
    OpenedSellStopOrderUpdateAPI,
    ModifiedBuyStopOrderVolumeUpdateAPI,
    ModifiedSellStopOrderVolumeUpdateAPI,
    ModifiedBuyStopOrderStopPriceUpdateAPI,
    ModifiedSellStopOrderStopPriceUpdateAPI,
    ModifiedBuyStopOrderStopLossUpdateAPI,
    ModifiedSellStopOrderStopLossUpdateAPI,
    ModifiedBuyStopOrderTakeProfitUpdateAPI,
    ModifiedSellStopOrderTakeProfitUpdateAPI,
    ClosedBuyStopOrderUpdateAPI,
    ClosedSellStopOrderUpdateAPI,
    FilledBuyStopOrderUpdateAPI,
    FilledSellStopOrderUpdateAPI,
    ExpiredBuyStopOrderUpdateAPI,
    ExpiredSellStopOrderUpdateAPI,
    OpenedBuyLimitOrderUpdateAPI,
    OpenedSellLimitOrderUpdateAPI,
    ModifiedBuyLimitOrderVolumeUpdateAPI,
    ModifiedSellLimitOrderVolumeUpdateAPI,
    ModifiedBuyLimitOrderLimitPriceUpdateAPI,
    ModifiedSellLimitOrderLimitPriceUpdateAPI,
    ModifiedBuyLimitOrderStopLossUpdateAPI,
    ModifiedSellLimitOrderStopLossUpdateAPI,
    ModifiedBuyLimitOrderTakeProfitUpdateAPI,
    ModifiedSellLimitOrderTakeProfitUpdateAPI,
    ClosedBuyLimitOrderUpdateAPI,
    ClosedSellLimitOrderUpdateAPI,
    FilledBuyLimitOrderUpdateAPI,
    FilledSellLimitOrderUpdateAPI,
    ExpiredBuyLimitOrderUpdateAPI,
    ExpiredSellLimitOrderUpdateAPI,
    OpenedBuyStopLimitOrderUpdateAPI,
    OpenedSellStopLimitOrderUpdateAPI,
    ModifiedBuyStopLimitOrderVolumeUpdateAPI,
    ModifiedSellStopLimitOrderVolumeUpdateAPI,
    ModifiedBuyStopLimitOrderStopPriceUpdateAPI,
    ModifiedSellStopLimitOrderStopPriceUpdateAPI,
    ModifiedBuyStopLimitOrderLimitPriceUpdateAPI,
    ModifiedSellStopLimitOrderLimitPriceUpdateAPI,
    ModifiedBuyStopLimitOrderStopLossUpdateAPI,
    ModifiedSellStopLimitOrderStopLossUpdateAPI,
    ModifiedBuyStopLimitOrderTakeProfitUpdateAPI,
    ModifiedSellStopLimitOrderTakeProfitUpdateAPI,
    ClosedBuyStopLimitOrderUpdateAPI,
    ClosedSellStopLimitOrderUpdateAPI,
    FilledBuyStopLimitOrderUpdateAPI,
    FilledSellStopLimitOrderUpdateAPI,
    ExpiredBuyStopLimitOrderUpdateAPI,
    ExpiredSellStopLimitOrderUpdateAPI,
    DeniedUpdateAPI,
    ExceptionUpdateAPI
)
from Library.System.Lifecycle import LifecycleAPI

if TYPE_CHECKING:
    from Library.Engine import MachineAPI
    from Library.Indicator.Fundamental import FundamentalAPI
    from Library.Indicator.Indicator import IndicatorAPI
    from Library.Indicator.Sentimental import SentimentalAPI
    from Library.Indicator.Technical import TechnicalAPI
    from Library.Market.Bar import BarAPI
    from Library.Market.Market import MarketAPI
    from Library.Market.Tick import TickAPI
    from Library.Parameters import Parameters
    from Library.Portfolio.Account import AccountAPI
    from Library.Portfolio.Portfolio import PortfolioAPI
    from Library.Strategy.Strategy import StrategyAPI
    from Library.Universe.Security import SecurityAPI
    from Library.Universe.Timeframe import TimeframeAPI

class SystemType(EnumerationAPI):
    Live = 1
    Simulation = 2
    Testing = 3
    Backtesting = 4
    Optimization = 5
    Learning = 6

class SystemAPI(ABC):

    def __init__(self,
                 strategy: Type[StrategyAPI],
                 security: SecurityAPI,
                 timeframe: TimeframeAPI,
                 parameters: Parameters,
                 market: tuple[int, float],
                 portfolio: tuple[int, float]) -> None:
        self._strategy_: Type[StrategyAPI] = strategy
        self._security_: SecurityAPI = security
        self._timeframe_: TimeframeAPI = timeframe
        self._parameters_: Parameters = parameters

        self.account: Union[AccountAPI, None] = None
        self.security: SecurityAPI = security
        self.market: Union[MarketAPI, None] = None
        self.indicator: Union[IndicatorAPI, None] = None
        self.technical: Union[TechnicalAPI, None] = None
        self.fundamental: Union[FundamentalAPI, None] = None
        self.sentimental: Union[SentimentalAPI, None] = None
        self.portfolio: Union[PortfolioAPI, None] = None
        self.strategy: Union[StrategyAPI, None] = None
        self.statistics = None

        self.buffer: BufferAPI = BufferAPI(market=market, portfolio=portfolio)

        self._log_: HandlerLoggingAPI = HandlerLoggingAPI(Class=self.__class__.__name__, Subclass="System Management")

    def __enter__(self) -> Self:
        self._log_.debug(lambda: "Initiated")
        if self.indicator is not None:
            self.technical = self.indicator.Technical
            self.fundamental = self.indicator.Fundamental
            self.sentimental = self.indicator.Sentimental
        if self.buffer.Active: self.buffer.start()
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback) -> Self:
        if exc_type or exc_value or exc_traceback:
            self._log_.exception(lambda: f"Exception type: {exc_type}")
            self._log_.exception(lambda: f"Exception value: {exc_value}")
            self._log_.exception(lambda: f"Traceback: {exc_traceback}")
        if self.buffer.Active: self.buffer.shutdown()
        self._log_.debug(lambda: "Terminated")
        return self

    @abstractmethod
    def send_action(self, action: ActionAPI) -> None:
        raise NotImplementedError

    @abstractmethod
    def receive_update_id(self) -> UpdateID:
        raise NotImplementedError

    @abstractmethod
    def receive_update_account(self) -> AccountAPI:
        raise NotImplementedError

    @abstractmethod
    def receive_update_security(self) -> SecurityAPI:
        raise NotImplementedError

    @abstractmethod
    def receive_update_target(self) -> TickAPI:
        raise NotImplementedError

    def _receive_update_target_(self) -> TickAPI:
        tick = self.receive_update_target()
        self.buffer.tick(tick)
        return tick

    @abstractmethod
    def receive_update_bar(self) -> BarAPI:
        raise NotImplementedError

    def _receive_update_bar_(self) -> BarAPI:
        bar = self.receive_update_bar()
        self.buffer.tick(bar.GapTick)
        self.buffer.tick(bar.OpenTick)
        self.buffer.tick(bar.HighTick)
        self.buffer.tick(bar.LowTick)
        self.buffer.tick(bar.CloseTick)
        self.buffer.bar(bar)
        return bar

    @abstractmethod
    def receive_update_order(self) -> OrderAPI:
        raise NotImplementedError

    def _receive_update_order_(self) -> OrderAPI:
        order = self.receive_update_order()
        self.buffer.order(order)
        return order

    @abstractmethod
    def receive_update_position(self) -> PositionAPI:
        raise NotImplementedError

    def _receive_update_position_(self) -> PositionAPI:
        position = self.receive_update_position()
        self.buffer.position(position)
        return position

    @abstractmethod
    def receive_update_trade(self) -> TradeAPI:
        raise NotImplementedError

    def _receive_update_trade_(self) -> TradeAPI:
        trade = self.receive_update_trade()
        self.buffer.trade(trade)
        return trade

    @abstractmethod
    def receive_update_denied(self) -> tuple[ActionID, str]:
        raise NotImplementedError

    @abstractmethod
    def receive_update_exception(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def system_management(self) -> MachineAPI:
        raise NotImplementedError

    def _process_updates_(self, engine: LifecycleAPI) -> list[ActionAPI]:
        actions: list[ActionAPI] = []
        while True:
            update_id = self.receive_update_id()
            match update_id:
                case UpdateID.Complete:
                    actions += engine.perform(update_id, CompleteUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio))
                    return actions
                case UpdateID.Shutdown:
                    actions += engine.perform(update_id, CompleteUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio))
                    return actions
                case UpdateID.Account:
                    self.account = self.receive_update_account()
                    actions += engine.perform(update_id, AccountUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio))
                case UpdateID.Security:
                    self.security = self.receive_update_security()
                    actions += engine.perform(update_id, SecurityUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio))
                case UpdateID.BarClosed:
                    actions += engine.perform(update_id, BarUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_()))
                case UpdateID.AskAboveTarget:
                    actions += engine.perform(update_id, TickUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Tick=self._receive_update_target_()))
                case UpdateID.AskBelowTarget:
                    actions += engine.perform(update_id, TickUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Tick=self._receive_update_target_()))
                case UpdateID.BidAboveTarget:
                    actions += engine.perform(update_id, TickUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Tick=self._receive_update_target_()))
                case UpdateID.BidBelowTarget:
                    actions += engine.perform(update_id, TickUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Tick=self._receive_update_target_()))
                case UpdateID.OpenedBuyPosition:
                    actions += engine.perform(update_id, OpenedBuyPositionUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Position=self._receive_update_position_()))
                case UpdateID.OpenedSellPosition:
                    actions += engine.perform(update_id, OpenedSellPositionUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Position=self._receive_update_position_()))
                case UpdateID.ModifiedBuyPositionVolume:
                    actions += engine.perform(update_id, ModifiedBuyPositionVolumeUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Position=self._receive_update_position_(), Trade=self._receive_update_trade_()))
                case UpdateID.ModifiedSellPositionVolume:
                    actions += engine.perform(update_id, ModifiedSellPositionVolumeUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Position=self._receive_update_position_(), Trade=self._receive_update_trade_()))
                case UpdateID.ModifiedBuyPositionStopLoss:
                    actions += engine.perform(update_id, ModifiedBuyPositionStopLossUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Position=self._receive_update_position_()))
                case UpdateID.ModifiedSellPositionStopLoss:
                    actions += engine.perform(update_id, ModifiedSellPositionStopLossUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Position=self._receive_update_position_()))
                case UpdateID.ModifiedBuyPositionTakeProfit:
                    actions += engine.perform(update_id, ModifiedBuyPositionTakeProfitUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Position=self._receive_update_position_()))
                case UpdateID.ModifiedSellPositionTakeProfit:
                    actions += engine.perform(update_id, ModifiedSellPositionTakeProfitUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Position=self._receive_update_position_()))
                case UpdateID.ClosedBuyPosition:
                    actions += engine.perform(update_id, ClosedBuyPositionUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Position=self._receive_update_position_(), Trade=self._receive_update_trade_()))
                case UpdateID.ClosedSellPosition:
                    actions += engine.perform(update_id, ClosedSellPositionUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Position=self._receive_update_position_(), Trade=self._receive_update_trade_()))
                case UpdateID.StopLossBuyPosition:
                    actions += engine.perform(update_id, StopLossBuyPositionUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Position=self._receive_update_position_(), Trade=self._receive_update_trade_()))
                case UpdateID.StopLossSellPosition:
                    actions += engine.perform(update_id, StopLossSellPositionUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Position=self._receive_update_position_(), Trade=self._receive_update_trade_()))
                case UpdateID.TakeProfitBuyPosition:
                    actions += engine.perform(update_id, TakeProfitBuyPositionUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Position=self._receive_update_position_(), Trade=self._receive_update_trade_()))
                case UpdateID.TakeProfitSellPosition:
                    actions += engine.perform(update_id, TakeProfitSellPositionUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Position=self._receive_update_position_(), Trade=self._receive_update_trade_()))
                case UpdateID.MarginCallBuyPosition:
                    actions += engine.perform(update_id, MarginCallBuyPositionUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Position=self._receive_update_position_(), Trade=self._receive_update_trade_()))
                case UpdateID.MarginCallSellPosition:
                    actions += engine.perform(update_id, MarginCallSellPositionUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Position=self._receive_update_position_(), Trade=self._receive_update_trade_()))
                case UpdateID.OpenedBuyStopOrder:
                    actions += engine.perform(update_id, OpenedBuyStopOrderUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Order=self._receive_update_order_()))
                case UpdateID.OpenedSellStopOrder:
                    actions += engine.perform(update_id, OpenedSellStopOrderUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Order=self._receive_update_order_()))
                case UpdateID.ModifiedBuyStopOrderVolume:
                    actions += engine.perform(update_id, ModifiedBuyStopOrderVolumeUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Order=self._receive_update_order_()))
                case UpdateID.ModifiedSellStopOrderVolume:
                    actions += engine.perform(update_id, ModifiedSellStopOrderVolumeUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Order=self._receive_update_order_()))
                case UpdateID.ModifiedBuyStopOrderStopPrice:
                    actions += engine.perform(update_id, ModifiedBuyStopOrderStopPriceUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Order=self._receive_update_order_()))
                case UpdateID.ModifiedSellStopOrderStopPrice:
                    actions += engine.perform(update_id, ModifiedSellStopOrderStopPriceUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Order=self._receive_update_order_()))
                case UpdateID.ModifiedBuyStopOrderStopLoss:
                    actions += engine.perform(update_id, ModifiedBuyStopOrderStopLossUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Order=self._receive_update_order_()))
                case UpdateID.ModifiedSellStopOrderStopLoss:
                    actions += engine.perform(update_id, ModifiedSellStopOrderStopLossUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Order=self._receive_update_order_()))
                case UpdateID.ModifiedBuyStopOrderTakeProfit:
                    actions += engine.perform(update_id, ModifiedBuyStopOrderTakeProfitUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Order=self._receive_update_order_()))
                case UpdateID.ModifiedSellStopOrderTakeProfit:
                    actions += engine.perform(update_id, ModifiedSellStopOrderTakeProfitUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Order=self._receive_update_order_()))
                case UpdateID.ClosedBuyStopOrder:
                    actions += engine.perform(update_id, ClosedBuyStopOrderUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Order=self._receive_update_order_()))
                case UpdateID.ClosedSellStopOrder:
                    actions += engine.perform(update_id, ClosedSellStopOrderUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Order=self._receive_update_order_()))
                case UpdateID.FilledBuyStopOrder:
                    actions += engine.perform(update_id, FilledBuyStopOrderUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Order=self._receive_update_order_(), Position=self._receive_update_position_()))
                case UpdateID.FilledSellStopOrder:
                    actions += engine.perform(update_id, FilledSellStopOrderUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Order=self._receive_update_order_(), Position=self._receive_update_position_()))
                case UpdateID.ExpiredBuyStopOrder:
                    actions += engine.perform(update_id, ExpiredBuyStopOrderUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Order=self._receive_update_order_()))
                case UpdateID.ExpiredSellStopOrder:
                    actions += engine.perform(update_id, ExpiredSellStopOrderUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Order=self._receive_update_order_()))
                case UpdateID.OpenedBuyLimitOrder:
                    actions += engine.perform(update_id, OpenedBuyLimitOrderUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Order=self._receive_update_order_()))
                case UpdateID.OpenedSellLimitOrder:
                    actions += engine.perform(update_id, OpenedSellLimitOrderUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Order=self._receive_update_order_()))
                case UpdateID.ModifiedBuyLimitOrderVolume:
                    actions += engine.perform(update_id, ModifiedBuyLimitOrderVolumeUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Order=self._receive_update_order_()))
                case UpdateID.ModifiedSellLimitOrderVolume:
                    actions += engine.perform(update_id, ModifiedSellLimitOrderVolumeUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Order=self._receive_update_order_()))
                case UpdateID.ModifiedBuyLimitOrderLimitPrice:
                    actions += engine.perform(update_id, ModifiedBuyLimitOrderLimitPriceUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Order=self._receive_update_order_()))
                case UpdateID.ModifiedSellLimitOrderLimitPrice:
                    actions += engine.perform(update_id, ModifiedSellLimitOrderLimitPriceUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Order=self._receive_update_order_()))
                case UpdateID.ModifiedBuyLimitOrderStopLoss:
                    actions += engine.perform(update_id, ModifiedBuyLimitOrderStopLossUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Order=self._receive_update_order_()))
                case UpdateID.ModifiedSellLimitOrderStopLoss:
                    actions += engine.perform(update_id, ModifiedSellLimitOrderStopLossUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Order=self._receive_update_order_()))
                case UpdateID.ModifiedBuyLimitOrderTakeProfit:
                    actions += engine.perform(update_id, ModifiedBuyLimitOrderTakeProfitUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Order=self._receive_update_order_()))
                case UpdateID.ModifiedSellLimitOrderTakeProfit:
                    actions += engine.perform(update_id, ModifiedSellLimitOrderTakeProfitUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Order=self._receive_update_order_()))
                case UpdateID.ClosedBuyLimitOrder:
                    actions += engine.perform(update_id, ClosedBuyLimitOrderUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Order=self._receive_update_order_()))
                case UpdateID.ClosedSellLimitOrder:
                    actions += engine.perform(update_id, ClosedSellLimitOrderUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Order=self._receive_update_order_()))
                case UpdateID.FilledBuyLimitOrder:
                    actions += engine.perform(update_id, FilledBuyLimitOrderUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Order=self._receive_update_order_(), Position=self._receive_update_position_()))
                case UpdateID.FilledSellLimitOrder:
                    actions += engine.perform(update_id, FilledSellLimitOrderUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Order=self._receive_update_order_(), Position=self._receive_update_position_()))
                case UpdateID.ExpiredBuyLimitOrder:
                    actions += engine.perform(update_id, ExpiredBuyLimitOrderUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Order=self._receive_update_order_()))
                case UpdateID.ExpiredSellLimitOrder:
                    actions += engine.perform(update_id, ExpiredSellLimitOrderUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Order=self._receive_update_order_()))
                case UpdateID.OpenedBuyStopLimitOrder:
                    actions += engine.perform(update_id, OpenedBuyStopLimitOrderUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Order=self._receive_update_order_()))
                case UpdateID.OpenedSellStopLimitOrder:
                    actions += engine.perform(update_id, OpenedSellStopLimitOrderUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Order=self._receive_update_order_()))
                case UpdateID.ModifiedBuyStopLimitOrderVolume:
                    actions += engine.perform(update_id, ModifiedBuyStopLimitOrderVolumeUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Order=self._receive_update_order_()))
                case UpdateID.ModifiedSellStopLimitOrderVolume:
                    actions += engine.perform(update_id, ModifiedSellStopLimitOrderVolumeUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Order=self._receive_update_order_()))
                case UpdateID.ModifiedBuyStopLimitOrderStopPrice:
                    actions += engine.perform(update_id, ModifiedBuyStopLimitOrderStopPriceUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Order=self._receive_update_order_()))
                case UpdateID.ModifiedSellStopLimitOrderStopPrice:
                    actions += engine.perform(update_id, ModifiedSellStopLimitOrderStopPriceUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Order=self._receive_update_order_()))
                case UpdateID.ModifiedBuyStopLimitOrderLimitPrice:
                    actions += engine.perform(update_id, ModifiedBuyStopLimitOrderLimitPriceUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Order=self._receive_update_order_()))
                case UpdateID.ModifiedSellStopLimitOrderLimitPrice:
                    actions += engine.perform(update_id, ModifiedSellStopLimitOrderLimitPriceUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Order=self._receive_update_order_()))
                case UpdateID.ModifiedBuyStopLimitOrderStopLoss:
                    actions += engine.perform(update_id, ModifiedBuyStopLimitOrderStopLossUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Order=self._receive_update_order_()))
                case UpdateID.ModifiedSellStopLimitOrderStopLoss:
                    actions += engine.perform(update_id, ModifiedSellStopLimitOrderStopLossUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Order=self._receive_update_order_()))
                case UpdateID.ModifiedBuyStopLimitOrderTakeProfit:
                    actions += engine.perform(update_id, ModifiedBuyStopLimitOrderTakeProfitUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Order=self._receive_update_order_()))
                case UpdateID.ModifiedSellStopLimitOrderTakeProfit:
                    actions += engine.perform(update_id, ModifiedSellStopLimitOrderTakeProfitUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Order=self._receive_update_order_()))
                case UpdateID.ClosedBuyStopLimitOrder:
                    actions += engine.perform(update_id, ClosedBuyStopLimitOrderUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Order=self._receive_update_order_()))
                case UpdateID.ClosedSellStopLimitOrder:
                    actions += engine.perform(update_id, ClosedSellStopLimitOrderUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Order=self._receive_update_order_()))
                case UpdateID.FilledBuyStopLimitOrder:
                    actions += engine.perform(update_id, FilledBuyStopLimitOrderUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Order=self._receive_update_order_(), Position=self._receive_update_position_()))
                case UpdateID.FilledSellStopLimitOrder:
                    actions += engine.perform(update_id, FilledSellStopLimitOrderUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Order=self._receive_update_order_(), Position=self._receive_update_position_()))
                case UpdateID.ExpiredBuyStopLimitOrder:
                    actions += engine.perform(update_id, ExpiredBuyStopLimitOrderUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Order=self._receive_update_order_()))
                case UpdateID.ExpiredSellStopLimitOrder:
                    actions += engine.perform(update_id, ExpiredSellStopLimitOrderUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self.receive_update_bar(), Order=self._receive_update_order_()))
                case UpdateID.Denied:
                    action_id, reason = self.receive_update_denied()
                    actions += engine.perform(update_id, DeniedUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, ActionID=action_id, Reason=reason))
                case UpdateID.Exception:
                    reason = self.receive_update_exception()
                    actions += engine.perform(update_id, ExceptionUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Reason=reason))

    def _process_actions_(self, actions: list[ActionAPI]) -> None:
        for action in actions: self.send_action(action)
        self.send_action(CompleteActionAPI())

    def deploy(self) -> None:
        engine = LifecycleAPI(
            system_machine=self.system_management(),
            strategy_machine=self.strategy.strategy_management(),
            signal_machine=self.strategy.signal_management(),
            risk_machine=self.strategy.risk_management()
        )
        while not engine.IsTerminated:
            actions = self._process_updates_(engine)
            self._process_actions_(actions)
            if not self.buffer.Empty: self.buffer.flush()
        self.buffer.flush()

    @abstractmethod
    def run(self) -> None:
        raise NotImplementedError

__all__ = ["SystemType", "SystemAPI"]
