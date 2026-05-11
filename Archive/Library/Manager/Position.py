import math

from Library.Classes import *
from Library.Manager import EPSILON

class PositionAPI:

    def __init__(self):
        self.Buys: dict[int, Position] = {}
        self.Sells: dict[int, Position] = {}

    @staticmethod
    def _open_position(positions: dict[int, Position], account: Account, new_position: Position) -> None:
        new_position.BaseBalance = new_position.EntryBalance = account.Balance
        positions[new_position.PositionID] = new_position

    @staticmethod
    def __modify_position(old_position: Position, new_position: Position) -> None:
        new_position.DrawdownPoints = old_position.DrawdownPoints
        new_position.DrawdownPips = old_position.DrawdownPips
        new_position.DrawdownPnL = old_position.DrawdownPnL
        new_position.BaseBalance = old_position.BaseBalance
        new_position.EntryBalance = old_position.EntryBalance

    @staticmethod
    def _modify_position(positions: dict[int, Position], new_position: Position) -> None:
        old_position = positions[new_position.PositionID]
        PositionAPI.__modify_position(old_position, new_position)
        positions[new_position.PositionID] = new_position

    @staticmethod
    def __close_position(old_position: Position, new_trade: Trade) -> None:
        if old_position.DrawdownPnL is not None and old_position.DrawdownPips <= new_trade.Pips:
            new_trade.DrawdownPoints = old_position.DrawdownPoints
            new_trade.DrawdownPips = old_position.DrawdownPips
            new_trade.DrawdownPnL = old_position.DrawdownPnL
        else:
            new_trade.DrawdownPoints = old_position.DrawdownPoints = min(old_position.DrawdownPoints, new_trade.Points)
            new_trade.DrawdownPips = old_position.DrawdownPips = min(old_position.DrawdownPips, new_trade.Pips)
            new_trade.DrawdownPnL = old_position.DrawdownPnL = min(new_trade.NetPnL * new_trade.DrawdownPips / new_trade.Pips, new_trade.NetPnL)
        new_trade.BaseBalance = old_position.BaseBalance
        new_trade.EntryBalance = old_position.EntryBalance
        new_trade.ExitBalance = old_position.EntryBalance = new_trade.EntryBalance + new_trade.NetPnL
        new_trade.NetReturn = new_trade.NetPnL / new_trade.BaseBalance
        new_trade.NetLogReturn = math.log(new_trade.ExitBalance / new_trade.EntryBalance)
        new_trade.DrawdownReturn = new_trade.DrawdownPnL / new_trade.BaseBalance
        new_trade.ReturnOverMaxDrawdown = new_trade.NetReturn / ((-1 * new_trade.DrawdownReturn) if new_trade.DrawdownReturn else EPSILON)

    @staticmethod
    def _close_position(positions: dict[int, Position], new_trade: Trade) -> None:
        old_position = positions[new_trade.PositionID]
        PositionAPI.__close_position(old_position, new_trade)
        del positions[new_trade.PositionID]

    @staticmethod
    def _modify_position_trade(positions: dict[int, Position], new_position: Position, new_trade: Trade) -> None:
        old_position = positions[new_position.PositionID]
        PositionAPI.__close_position(old_position, new_trade)
        PositionAPI.__modify_position(old_position, new_position)
        positions[new_position.PositionID] = new_position

    def open_position_buy(self, account: Account, position: Position) -> None:
        return self._open_position(self.Buys, account, position)

    def open_position_sell(self, account: Account, position: Position) -> None:
        return self._open_position(self.Sells, account, position)

    def modify_position_buy(self, position: Position) -> None:
        return self._modify_position(self.Buys, position)

    def modify_position_sell(self, position: Position) -> None:
        return self._modify_position(self.Sells, position)

    def modify_position_trade_buy(self, position: Position, trade: Trade) -> None:
        return self._modify_position_trade(self.Buys, position, trade)

    def modify_position_trade_sell(self, position: Position, trade: Trade) -> None:
        return self._modify_position_trade(self.Sells, position, trade)

    def close_position_buy(self, trade: Trade) -> None:
        return self._close_position(self.Buys, trade)

    def close_position_sell(self, trade: Trade) -> None:
        return self._close_position(self.Sells, trade)

    def update_position(self, security: Security, bar: Bar) -> None:
        for position in self.Buys.values():
            drawdown = (bar.LowPrice.Price - position.EntryPrice.Price)
            position.DrawdownPoints = min(position.DrawdownPoints, drawdown / security.PointSize)
            position.DrawdownPips = min(position.DrawdownPips, drawdown / security.PipSize)
        for position in self.Sells.values():
            drawdown = (position.EntryPrice.Price - bar.HighPrice.Price)
            position.DrawdownPoints = min(position.DrawdownPoints, drawdown / security.PointSize)
            position.DrawdownPips = min(position.DrawdownPips, drawdown / security.PipSize)

    def data(self):
        return self.Buys, self.Sells

    def __repr__(self) -> str:
        return repr(self.data())