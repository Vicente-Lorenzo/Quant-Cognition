from __future__ import annotations

from typing import Union
import clr
clr.AddReference("cAlgo.API")
from cAlgo.API import *

from Library.Logging import LoggingAPI, ConsoleAPI, TelegramAPI, FileAPI, HandlerAPI, VerboseType
from Library.Parameters import ParametersAPI
from Library.Strategy import DownloadStrategyAPI, NNFXStrategyAPI, DDPGStrategyAPI
from Library.Classes import StrategyType
from Library.System.Trading import TradingSystemAPI

_STRATEGIES_ = {
    StrategyType.Download.name: DownloadStrategyAPI,
    StrategyType.NNFX.name: NNFXStrategyAPI,
    StrategyType.DDPG.name: DDPGStrategyAPI
}

class TradingBot:

    def __init__(self, api, strategy: str, group: str, console: str, telegram: str, file: str) -> None:
        self.api = api
        self.strategy_name = strategy
        self.group = group
        self.console = console
        self.telegram = telegram
        self.file = file
        self.system: Union[TradingSystemAPI, None] = None
        self._log_: Union[HandlerAPI, None] = None

    def on_start(self) -> None:
        broker = self.api.Account.BrokerName.replace(" ", "")
        symbol = self.api.Symbol.Name.replace(" ", "")
        timeframe = self.api.TimeFrame.Name.replace(" ", "")

        LoggingAPI.init(
            System="Trading",
            Strategy=self.strategy_name,
            Broker=broker,
            Group=self.group,
            Symbol=symbol,
            Timeframe=timeframe
        )
        ConsoleAPI.setup(VerboseType[self.console])
        TelegramAPI.setup(VerboseType[self.telegram], uid=self.group)
        FileAPI.setup(VerboseType[self.file], uid=["Trading"])

        self._log_ = HandlerAPI(Class="TradingBot", Subclass="Bootstrap")

        strategy_cls = _STRATEGIES_[self.strategy_name]
        parameters = ParametersAPI()[broker][self.group][symbol][timeframe].Trading[self.strategy_name]

        self.system = TradingSystemAPI(
            api=self.api,
            broker=broker,
            group=self.group,
            symbol=symbol,
            timeframe=timeframe,
            strategy=strategy_cls,
            parameters=parameters
        )
        self.system.__enter__()
        self.system.start()

    def on_tick(self) -> None:
        if self.system is not None:
            self.system.on_tick()

    def on_bar_closed(self) -> None:
        if self.system is not None:
            self.system.on_bar_closed()

    def on_stop(self) -> None:
        if self.system is not None:
            self.system.on_shutdown()
            self.system.__exit__(None, None, None)

    def on_error(self, error) -> None:
        if self._log_ is not None:
            self._log_.error(lambda: f"Error: {error}")

    def on_exception(self, exception) -> None:
        if self._log_ is not None:
            self._log_.exception(lambda: f"Exception: {exception}")
