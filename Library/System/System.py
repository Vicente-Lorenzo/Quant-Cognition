from __future__ import annotations

from typing import Union, Type, TYPE_CHECKING
from abc import ABC, abstractmethod
from threading import Thread

from Library.Database.Dataframe import pl
from Library.Logging import HandlerAPI
from Library.Engine import MachineAPI, EngineAPI

if TYPE_CHECKING:
    from Library.Portfolio.Account import AccountAPI
    from Library.Universe.Security import SecurityAPI
    from Library.Portfolio.Position import PositionAPI
    from Library.Portfolio.Trade import TradeAPI
    from Library.Market.Bar import BarAPI
    from Library.Market.Tick import TickAPI
    from Library.Parameters import Parameters
    from Library.Strategy import StrategyAPI
    from Library.Market.Market import MarketAPI
    from Library.Portfolio.Portfolio import PortfolioAPI
    from Library.Utility import (
        CompleteAction,
        OpenBuyAction,
        OpenSellAction,
        ModifyBuyVolumeAction,
        ModifySellVolumeAction,
        ModifyBuyStopLossAction,
        ModifySellStopLossAction,
        ModifyBuyTakeProfitAction,
        ModifySellTakeProfitAction,
        CloseBuyAction,
        CloseSellAction,
        AskAboveTargetAction,
        AskBelowTargetAction,
        BidAboveTargetAction,
        BidBelowTargetAction,
        UpdateID,
        CompleteUpdate,
        AccountUpdate,
        SymbolUpdate,
        PositionUpdate,
        PositionTradeUpdate,
        TradeUpdate,
        BarUpdate,
        TickUpdate
    )

class SystemAPI(Thread, ABC):

    def __init__(self,
                 broker: str,
                 group: str,
                 symbol: str,
                 timeframe: str,
                 strategy: Type[StrategyAPI],
                 parameters: Parameters) -> None:
        
        super().__init__(daemon=True)

        self._broker: str = broker
        self._group: str = group
        self._symbol: str = symbol
        self._timeframe: str = timeframe
        
        self._strategy_: Type[StrategyAPI] = strategy
        
        self.parameters: Parameters = parameters

        self.strategy: Union[StrategyAPI, None] = None
        self.market: Union[MarketAPI, None] = None
        self.indicator: Union[IndicatorAPI, None] = None
        self.portfolio: Union[PortfolioAPI, None] = None
        
        self.individual_trades: Union[pl.DataFrame, None] = None
        self.aggregated_trades: Union[pl.DataFrame, None] = None
        self.statistics: Union[pl.DataFrame, None] = None

        self._log: HandlerAPI = HandlerAPI(Class=self.__class__.__name__, Subclass="System Management")

    def __enter__(self) -> Self:
        self._log.debug(lambda: "Initiated")
        return self
    
    def __exit__(self, exc_type, exc_value, exc_traceback) -> Self:
        if exc_type or exc_value or exc_traceback:
            self._log.exception(lambda: f"Exception type: {exc_type}")
            self._log.exception(lambda: f"Exception value: {exc_value}")
            self._log.exception(lambda: f"Traceback: {exc_traceback}")
        self._log.debug(lambda: "Terminated")
        return self

    @abstractmethod
    def send_action_complete(self, action: CompleteAction) -> None:
        raise NotImplementedError

    @abstractmethod
    def send_action_open(self, action: Union[OpenBuyAction, OpenSellAction]) -> None:
        raise NotImplementedError

    @abstractmethod
    def send_action_modify_volume(self, action: Union[ModifyBuyVolumeAction, ModifySellVolumeAction]) -> None:
        raise NotImplementedError

    @abstractmethod
    def send_action_modify_stop_loss(self, action: Union[ModifyBuyStopLossAction, ModifySellStopLossAction]) -> None:
        raise NotImplementedError

    @abstractmethod
    def send_action_modify_take_profit(self, action: Union[ModifyBuyTakeProfitAction, ModifySellTakeProfitAction]) -> None:
        raise NotImplementedError
    
    @abstractmethod
    def send_action_close(self, action: Union[CloseBuyAction, CloseSellAction]) -> None:
        raise NotImplementedError

    @abstractmethod
    def send_action_ask_above_target(self, action: AskAboveTargetAction) -> None:
        raise NotImplementedError

    @abstractmethod
    def send_action_ask_below_target(self, action: AskBelowTargetAction) -> None:
        raise NotImplementedError

    @abstractmethod
    def send_action_bid_above_target(self, action: BidAboveTargetAction) -> None:
        raise NotImplementedError

    @abstractmethod
    def send_action_bid_below_target(self, action: BidBelowTargetAction) -> None:
        raise NotImplementedError

    @abstractmethod
    def receive_update_id(self) -> UpdateID:
        raise NotImplementedError

    @abstractmethod
    def receive_update_account(self) -> AccountAPI:
        raise NotImplementedError

    @abstractmethod
    def receive_update_symbol(self) -> SecurityAPI:
        raise NotImplementedError

    @abstractmethod
    def receive_update_position(self) -> PositionAPI:
        raise NotImplementedError

    @abstractmethod
    def receive_update_trade(self) -> TradeAPI:
        raise NotImplementedError

    @abstractmethod
    def receive_update_bar(self) -> BarAPI:
        raise NotImplementedError

    @abstractmethod
    def receive_update_target(self) -> TickAPI:
        raise NotImplementedError

    @abstractmethod
    def system_management(self) -> MachineAPI:
        raise NotImplementedError

    def deploy(self, strategy: StrategyAPI, market: MarketAPI, indicator: IndicatorAPI, portfolio: PortfolioAPI) -> None:
        from Library.Utility import (
            CompleteUpdate, AccountUpdate, SymbolUpdate, PositionUpdate, 
            PositionTradeUpdate, TradeUpdate, BarUpdate, TickUpdate, UpdateID, ActionID, CompleteAction
        )
        system = EngineAPI(system_engine=self.system_management(),
                           strategy_engine=strategy.strategy_management(),
                           signal_engine=strategy.signal_management(),
                           risk_engine=strategy.risk_management())
        while not system.is_terminated():
            actions = []
            while True:
                update_id = self.receive_update_id()
                match update_id:
                    case UpdateID.Complete:
                        actions += system.perform_update_complete(CompleteUpdate(market, indicator, portfolio))
                        break
                    case UpdateID.Account:
                        actions += system.perform_update_account(AccountUpdate(market, indicator, portfolio, self.receive_update_account()))
                    case UpdateID.Symbol:
                        actions += system.perform_update_symbol(SymbolUpdate(market, indicator, portfolio, self.receive_update_symbol()))
                    case UpdateID.OpenedBuy:
                        actions += system.perform_update_opened_buy(PositionUpdate(market, indicator, portfolio, self.receive_update_bar(), self.receive_update_account(), self.receive_update_position()))
                    case UpdateID.OpenedSell:
                        actions += system.perform_update_opened_sell(PositionUpdate(market, indicator, portfolio, self.receive_update_bar(), self.receive_update_account(), self.receive_update_position()))
                    case UpdateID.ModifiedBuyVolume:
                        actions += system.perform_update_modified_volume_buy(PositionTradeUpdate(market, indicator, portfolio, self.receive_update_bar(), self.receive_update_account(), self.receive_update_position(), self.receive_update_trade()))
                    case UpdateID.ModifiedBuyStopLoss:
                        actions += system.perform_update_modified_stop_loss_buy(PositionUpdate(market, indicator, portfolio, self.receive_update_bar(), self.receive_update_account(), self.receive_update_position()))
                    case UpdateID.ModifiedBuyTakeProfit:
                        actions += system.perform_update_modified_take_profit_buy(PositionUpdate(market, indicator, portfolio, self.receive_update_bar(), self.receive_update_account(), self.receive_update_position()))
                    case UpdateID.ModifiedSellVolume:
                        actions += system.perform_update_modified_volume_sell(PositionTradeUpdate(market, indicator, portfolio, self.receive_update_bar(), self.receive_update_account(), self.receive_update_position(), self.receive_update_trade()))
                    case UpdateID.ModifiedSellStopLoss:
                        actions += system.perform_update_modified_stop_loss_sell(PositionUpdate(market, indicator, portfolio, self.receive_update_bar(), self.receive_update_account(), self.receive_update_position()))
                    case UpdateID.ModifiedSellTakeProfit:
                        actions += system.perform_update_modified_take_profit_sell(PositionUpdate(market, indicator, portfolio, self.receive_update_bar(), self.receive_update_account(), self.receive_update_position()))
                    case UpdateID.ClosedBuy:
                        actions += system.perform_update_closed_buy(TradeUpdate(market, indicator, portfolio, self.receive_update_bar(), self.receive_update_account(), self.receive_update_trade()))
                    case UpdateID.ClosedSell:
                        actions += system.perform_update_closed_sell(TradeUpdate(market, indicator, portfolio, self.receive_update_bar(), self.receive_update_account(), self.receive_update_trade()))
                    case UpdateID.BarClosed:
                        actions += system.perform_update_bar_closed(BarUpdate(market, indicator, portfolio, self.receive_update_bar()))
                    case UpdateID.AskAboveTarget:
                        actions += system.perform_update_ask_above_target(TickUpdate(market, indicator, portfolio, self.receive_update_target()))
                    case UpdateID.AskBelowTarget:
                        actions += system.perform_update_ask_below_target(TickUpdate(market, indicator, portfolio, self.receive_update_target()))
                    case UpdateID.BidAboveTarget:
                        actions += system.perform_update_bid_above_target(TickUpdate(market, indicator, portfolio, self.receive_update_target()))
                    case UpdateID.BidBelowTarget:
                        actions += system.perform_update_bid_below_target(TickUpdate(market, indicator, portfolio, self.receive_update_target()))
                    case UpdateID.Shutdown:
                        self._log.debug(lambda: "Shutdown")
                        actions += system.perform_update_shutdown(CompleteUpdate(market, indicator, portfolio))
                        break
                    case _:
                        self._log.error(lambda: f"Received invalid update ID: {update_id}")
                        raise
            for action in actions:
                match action.ActionID:
                    case ActionID.Complete:
                        self.send_action_complete(action)
                    case ActionID.OpenBuy | ActionID.OpenSell:
                        self.send_action_open(action)
                    case ActionID.ModifyBuyVolume | ActionID.ModifySellVolume:
                        self.send_action_modify_volume(action)
                    case ActionID.ModifyBuyStopLoss | ActionID.ModifySellStopLoss:
                        self.send_action_modify_stop_loss(action)
                    case ActionID.ModifyBuyTakeProfit | ActionID.ModifySellTakeProfit:
                        self.send_action_modify_take_profit(action)
                    case ActionID.CloseBuy | ActionID.CloseSell:
                        self.send_action_close(action)
                    case ActionID.AskAboveTarget:
                        self.send_action_ask_above_target(action)
                    case ActionID.AskBelowTarget:
                        self.send_action_ask_below_target(action)
                    case ActionID.BidAboveTarget:
                        self.send_action_bid_above_target(action)
                    case ActionID.BidBelowTarget:
                        self.send_action_bid_below_target(action)
                    case _:
                        self._log.error(lambda: f"Sent invalid action ID: {action.ActionID}")
                        raise
            self.send_action_complete(CompleteAction())
                    
    @abstractmethod
    def run(self) -> None:
        raise NotImplementedError
