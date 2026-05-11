from __future__ import annotations

from typing import Union, TYPE_CHECKING
from abc import ABC, abstractmethod

from Library.Logging import HandlerAPI

if TYPE_CHECKING:
    from Library.Parameters import Parameters
    from Library.Engine import MachineAPI
    from Library.Utility import (
        PositionUpdate,
        PositionTradeUpdate,
        TradeUpdate,
        AccountUpdate,
        SymbolUpdate,
        BarUpdate
    )

class StrategyAPI(ABC):

    OPENED_BUY = "Opened Buy ({0} Position)"
    OPENED_SELL = "Opened Sell ({0} Position)"
    MODIFIED_VOLUME_BUY = "Modified Buy Volume ({0} Position)"
    MODIFIED_VOLUME_SELL = "Modified Sell Volume ({0} Position)"
    MODIFIED_STOPLOSS_BUY = "Modified Buy Stop-Loss ({0} Position)"
    MODIFIED_STOPLOSS_SELL = "Modified Sell Stop-Loss ({0} Position)"
    MODIFIED_TAKEPROFIT_BUY = "Modified Buy Take-Profit ({0} Position)"
    MODIFIED_TAKEPROFIT_SELL = "Modified Sell Take-Profit ({0} Position)"
    CLOSED_BUY = "Closed Buy ({0} Position)"
    CLOSED_SELL = "Closed Sell ({0} Position)"

    def __init__(self,
                 money_management: Parameters,
                 risk_management: Parameters,
                 signal_management: Parameters) -> None:

        self.MoneyManagement: Parameters = money_management
        self.RiskManagement: Parameters = risk_management
        self.SignalManagement: Parameters = signal_management

        self._log_: HandlerAPI = HandlerAPI(Class=self.__class__.__name__, Subclass="Strategy Management")

    def _log_opened_buy_(self, update: PositionUpdate) -> None:
        self._log_.alert(lambda: StrategyAPI.OPENED_BUY.format(update.Position.Type.name))

    def _log_opened_sell_(self, update: PositionUpdate) -> None:
        self._log_.alert(lambda: StrategyAPI.OPENED_SELL.format(update.Position.Type.name))

    def _log_modified_volume_buy_(self, update: PositionTradeUpdate) -> None:
        self._log_.alert(lambda: StrategyAPI.MODIFIED_VOLUME_BUY.format(update.Position.Type.name))

    def _log_modified_volume_sell_(self, update: PositionTradeUpdate) -> None:
        self._log_.alert(lambda: StrategyAPI.MODIFIED_VOLUME_SELL.format(update.Position.Type.name))

    def _log_modified_stop_loss_buy_(self, update: PositionUpdate) -> None:
        self._log_.alert(lambda: StrategyAPI.MODIFIED_STOPLOSS_BUY.format(update.Position.Type.name))

    def _log_modified_stop_loss_sell_(self, update: PositionUpdate) -> None:
        self._log_.alert(lambda: StrategyAPI.MODIFIED_STOPLOSS_SELL.format(update.Position.Type.name))

    def _log_modified_take_profit_buy_(self, update: PositionUpdate) -> None:
        self._log_.alert(lambda: StrategyAPI.MODIFIED_TAKEPROFIT_BUY.format(update.Position.Type.name))

    def _log_modified_take_profit_sell_(self, update: PositionUpdate) -> None:
        self._log_.alert(lambda: StrategyAPI.MODIFIED_TAKEPROFIT_SELL.format(update.Position.Type.name))

    def _log_closed_buy_(self, update: TradeUpdate) -> None:
        self._log_.alert(lambda: StrategyAPI.CLOSED_BUY.format(update.Trade.Type.name))

    def _log_closed_sell_(self, update: TradeUpdate) -> None:
        self._log_.alert(lambda: StrategyAPI.CLOSED_SELL.format(update.Trade.Type.name))

    @abstractmethod
    def risk_management(self) -> Union[MachineAPI, None]:
        raise NotImplementedError

    @abstractmethod
    def signal_management(self) -> Union[MachineAPI, None]:
        raise NotImplementedError

    def strategy_management(self) -> Union[MachineAPI, None]:
        from Library.Engine import MachineAPI
        strategy_engine = MachineAPI("Strategy Management")

        initialisation = strategy_engine.create_state(name="Initialisation", end=False)
        execution = strategy_engine.create_state(name="Execution", end=False)
        termination = strategy_engine.create_state(name="Termination", end=True)

        def init_account(update: AccountUpdate):
            update.Portfolio.update_account(update.Account)

        def init_symbol(update: SymbolUpdate):
            update.Portfolio._security_ = update.Security

        def update_bar(update: BarUpdate):
            update.Portfolio.update_market_data(update.Bar)

        def update_opened_buy(update: PositionUpdate):
            update.Portfolio.update_account(update.Account)
            update.Portfolio.update_market_data(update.Bar)
            update.Portfolio.fill_position(update.Position.Order.UID if update.Position.Order else 0, update.Position)
            self._log_opened_buy_(update)

        def update_opened_sell(update: PositionUpdate):
            update.Portfolio.update_account(update.Account)
            update.Portfolio.update_market_data(update.Bar)
            update.Portfolio.fill_position(update.Position.Order.UID if update.Position.Order else 0, update.Position)
            self._log_opened_sell_(update)

        def update_modified_buy_volume(update: PositionTradeUpdate):
            update.Portfolio.update_account(update.Account)
            update.Portfolio.update_market_data(update.Bar)
            update.Portfolio.close_trade(update.Position.UID, update.Trade)
            self._log_modified_volume_buy_(update)

        def update_modified_buy_stop_loss(update: PositionUpdate):
            update.Portfolio.update_account(update.Account)
            update.Portfolio.update_market_data(update.Bar)
            update.Portfolio.modify_position(update.Position)
            self._log_modified_stop_loss_buy_(update)

        def update_modified_buy_take_profit(update: PositionUpdate):
            update.Portfolio.update_account(update.Account)
            update.Portfolio.update_market_data(update.Bar)
            update.Portfolio.modify_position(update.Position)
            self._log_modified_take_profit_buy_(update)

        def update_modified_sell_volume(update: PositionTradeUpdate):
            update.Portfolio.update_account(update.Account)
            update.Portfolio.update_market_data(update.Bar)
            update.Portfolio.close_trade(update.Position.UID, update.Trade)
            self._log_modified_volume_sell_(update)

        def update_modified_sell_stop_loss(update: PositionUpdate):
            update.Portfolio.update_account(update.Account)
            update.Portfolio.update_market_data(update.Bar)
            update.Portfolio.modify_position(update.Position)
            self._log_modified_stop_loss_sell_(update)

        def update_modified_sell_take_profit(update: PositionUpdate):
            update.Portfolio.update_account(update.Account)
            update.Portfolio.update_market_data(update.Bar)
            update.Portfolio.modify_position(update.Position)
            self._log_modified_take_profit_sell_(update)

        def update_closed_buy(update: TradeUpdate):
            update.Portfolio.update_account(update.Account)
            update.Portfolio.update_market_data(update.Bar)
            update.Portfolio.close_trade(update.Trade.Position.UID if update.Trade.Position else 0, update.Trade)
            self._log_closed_buy_(update)

        def update_closed_sell(update: TradeUpdate):
            update.Portfolio.update_account(update.Account)
            update.Portfolio.update_market_data(update.Bar)
            update.Portfolio.close_trade(update.Trade.Position.UID if update.Trade.Position else 0, update.Trade)
            self._log_closed_sell_(update)

        initialisation.on_account(to=initialisation, action=init_account, reason="Account Initialized")
        initialisation.on_symbol(to=initialisation, action=init_symbol, reason="Symbol Initialized")
        initialisation.on_complete(to=execution, action=None, reason="Initialized")
        initialisation.on_shutdown(to=termination, action=None, reason="Abruptly Terminated")

        execution.on_bar_closed(to=execution, action=update_bar, reason=None)
        execution.on_opened_buy(to=execution, action=update_opened_buy, reason="Opened Buy Position")
        execution.on_opened_sell(to=execution, action=update_opened_sell, reason="Opened Sell Position")
        execution.on_modified_volume_buy(to=execution, action=update_modified_buy_volume, reason="Modified Buy Volume")
        execution.on_modified_stop_loss_buy(to=execution, action=update_modified_buy_stop_loss, reason="Modified Buy Stop-Loss")
        execution.on_modified_take_profit_buy(to=execution, action=update_modified_buy_take_profit, reason="Modified Buy Take-Profit")
        execution.on_modified_volume_sell(to=execution, action=update_modified_sell_volume, reason="Modified Sell Volume")
        execution.on_modified_stop_loss_sell(to=execution, action=update_modified_sell_stop_loss, reason="Modified Sell Stop-Loss")
        execution.on_modified_take_profit_sell(to=execution, action=update_modified_sell_take_profit, reason="Modified Sell Take-Profit")
        execution.on_closed_buy(to=execution, action=update_closed_buy, reason="Closed Buy Position")
        execution.on_closed_sell(to=execution, action=update_closed_sell, reason="Closed Sell Position")
        execution.on_shutdown(to=termination, action=None, reason="Safely Terminated")

        return strategy_engine
