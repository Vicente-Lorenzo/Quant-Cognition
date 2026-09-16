from __future__ import annotations

from datetime import datetime
from dataclasses import dataclass, field
from typing import Union, ClassVar, TYPE_CHECKING

from Library.Database.Dataframe import pl
from Library.Database.Datapoint import DatapointAPI
from Library.Database.Query import QueryAPI
from Library.Market.Price import Direction, PriceAPI, calculate_direction
from Library.Market.Tick import TickAPI
from Library.Portfolio.PnL import PnLAPI
from Library.Statistic.Metric import (
    calculate_annualized_log_return,
    calculate_annualized_return,
    calculate_gross_pnl,
    calculate_log_percentage,
    calculate_log_return,
    calculate_net_pnl,
    calculate_percentage,
    calculate_pnl_difference,
    calculate_pnl_return
)

if TYPE_CHECKING:
    from Library.Database.Database import DatabaseAPI
    from Library.Portfolio.Account import AccountAPI
    from Library.Portfolio.Order import OrderAPI
    from Library.Portfolio.Position import PositionAPI
    from Library.Portfolio.Trade import TradeAPI
    from Library.Market.Bar import BarAPI
    from Library.Universe.Security import SecurityAPI

@dataclass(kw_only=True)
class PortfolioAPI(DatapointAPI):

    Schema: ClassVar[str] = "Portfolio"
    Table: ClassVar[str] = "Portfolio"

    _account_: Union[AccountAPI, None] = field(default=None, init=False)
    _security_: Union[SecurityAPI, None] = field(default=None, init=False)
    _orders_: dict[int, OrderAPI] = field(default_factory=dict, init=False)
    _positions_: dict[int, PositionAPI] = field(default_factory=dict, init=False)
    _trades_: list[TradeAPI] = field(default_factory=list, init=False)

    _initial_balance_: Union[float, None] = field(default=None, init=False)
    _equity_peak_: Union[float, None] = field(default=None, init=False)
    _equity_trough_: Union[float, None] = field(default=None, init=False)
    _equity_curve_: list = field(default_factory=list, init=False)
    _equity_stamp_: Union[datetime, None] = field(default=None, init=False)
    _excursion_peak_: Union[float, None] = field(default=None, init=False)
    _excursion_trough_: Union[float, None] = field(default=None, init=False)
    _max_drawdown_: float = field(default=0.0, init=False)
    _max_drawdown_value_: float = field(default=0.0, init=False)
    _max_runup_: float = field(default=0.0, init=False)
    _max_runup_value_: float = field(default=0.0, init=False)
    _drawdown_sum_: float = field(default=0.0, init=False)
    _drawdown_value_sum_: float = field(default=0.0, init=False)
    _runup_sum_: float = field(default=0.0, init=False)
    _runup_value_sum_: float = field(default=0.0, init=False)
    _excursion_count_: int = field(default=0, init=False)
    _excursion_stamp_: Union[datetime, None] = field(default=None, init=False)
    _last_conversion_: float = field(default=1.0, init=False)

    def __post_init__(self,
                      db: Union[DatabaseAPI, None],
                      migrate: bool,
                      autosave: bool,
                      autoload: bool,
                      autooverload: bool) -> None:
        super().__post_init__(db=db, migrate=migrate, autosave=autosave, autoload=autoload, autooverload=autooverload)

    @staticmethod
    def pull_accounts(db: DatabaseAPI) -> pl.DataFrame:
        from Library.Portfolio.Account import AccountAPI
        sql = f'''
        SELECT a.*,
               p."UID" AS "Provider_UID", p."Platform" AS "Provider_Platform", p."Name" AS "Provider_Name", p."Abbreviation" AS "Provider_Abbreviation"
        FROM "{AccountAPI.Schema}"."{AccountAPI.Table}" a
        LEFT JOIN "Universe"."Provider" p ON a."Provider" = p."UID"
        '''
        df = db.executeone(QueryAPI(sql), schema=AccountAPI.Schema, table=AccountAPI.Table).fetchall(legacy=False)
        return df

    @staticmethod
    def push_accounts(db: DatabaseAPI, data: Union[pl.DataFrame, list[dict], tuple, dict]) -> None:
        from Library.Portfolio.Account import AccountAPI
        db.upsert(schema=AccountAPI.Schema, table=AccountAPI.Table, data=data, key=["UID"])

    @staticmethod
    def push_orders(db: DatabaseAPI, data: Union[pl.DataFrame, list[dict], tuple, dict]) -> None:
        from Library.Portfolio.Order import OrderAPI
        db.upsert(schema=OrderAPI.Schema, table=OrderAPI.Table, data=data, key=["UID"])

    @staticmethod
    def push_positions(db: DatabaseAPI, data: Union[pl.DataFrame, list[dict], tuple, dict]) -> None:
        from Library.Portfolio.Position import PositionAPI
        db.upsert(schema=PositionAPI.Schema, table=PositionAPI.Table, data=data, key=["UID"])

    @staticmethod
    def push_trades(db: DatabaseAPI, data: Union[pl.DataFrame, list[dict], tuple, dict]) -> None:
        from Library.Portfolio.Trade import TradeAPI
        db.upsert(schema=TradeAPI.Schema, table=TradeAPI.Table, data=data, key=["UID"])

    def init_data(self, account: AccountAPI, orders: list[OrderAPI] = None, positions: list[PositionAPI] = None, trades: list[TradeAPI] = None) -> None:
        self._account_ = account
        if orders:
            for o in orders: self._orders_[o.UID] = o
        if positions:
            for p in positions: self._positions_[p.UID] = p
        if trades:
            self._trades_.extend(trades)
        self._initial_balance_ = account.Balance if account and account.Balance is not None else 0.0
        self._equity_peak_ = self.Equity
        self._equity_trough_ = self.Equity

    def _track_equity_(self) -> None:
        equity = self.Equity
        if self._equity_peak_ is None or equity > self._equity_peak_: self._equity_peak_ = equity
        if self._equity_trough_ is None or equity < self._equity_trough_: self._equity_trough_ = equity

    def _record_equity_(self) -> None:
        if self._equity_stamp_ is None: return
        equity = self.Equity
        if self._equity_curve_ and self._equity_curve_[-1][0] == self._equity_stamp_: self._equity_curve_[-1] = (self._equity_stamp_, equity)
        else: self._equity_curve_.append((self._equity_stamp_, equity))

    def _accumulate_excursion_(self, equity: float) -> None:
        if self._excursion_peak_ is None or equity > self._excursion_peak_: self._excursion_peak_ = equity
        if self._excursion_trough_ is None or equity < self._excursion_trough_: self._excursion_trough_ = equity
        drawdown_value = self._excursion_peak_ - equity
        runup_value = equity - self._excursion_trough_
        drawdown = drawdown_value / self._excursion_peak_ if self._excursion_peak_ else 0.0
        runup = runup_value / self._excursion_trough_ if self._excursion_trough_ else 0.0
        if drawdown > self._max_drawdown_: self._max_drawdown_ = drawdown
        if drawdown_value > self._max_drawdown_value_: self._max_drawdown_value_ = drawdown_value
        if runup > self._max_runup_: self._max_runup_ = runup
        if runup_value > self._max_runup_value_: self._max_runup_value_ = runup_value
        self._drawdown_sum_ += drawdown
        self._drawdown_value_sum_ += drawdown_value
        self._runup_sum_ += runup
        self._runup_value_sum_ += runup_value
        self._excursion_count_ += 1

    @staticmethod
    def _conversion_(ask: Union[PriceAPI, None], bid: Union[PriceAPI, None]) -> float:
        a = ask.Price if ask else None
        b = bid.Price if bid else None
        if b is not None: return b
        return a if a is not None else 1.0

    def update_data(self, data: Union[TickAPI, BarAPI]) -> None:
        if isinstance(data, TickAPI):
            bid, ask, timestamp = data.Bid.Price, data.Ask.Price, data.Timestamp.DateTime
            high_bid = low_bid = bid
            high_ask = low_ask = ask
            conversion = self._conversion_(data.AskQuoteConversion, data.BidQuoteConversion)
        else:
            bid, ask, timestamp = data.CloseTick.Bid.Price, data.CloseTick.Ask.Price, data.Timestamp.DateTime
            high_bid = data.HighTick.Bid.Price if data.HighTick and data.HighTick.Bid else bid
            low_bid = data.LowTick.Bid.Price if data.LowTick and data.LowTick.Bid else bid
            high_ask = data.HighTick.Ask.Price if data.HighTick and data.HighTick.Ask else ask
            low_ask = data.LowTick.Ask.Price if data.LowTick and data.LowTick.Ask else ask
            conversion = self._conversion_(data.CloseTick.AskQuoteConversion, data.CloseTick.BidQuoteConversion)
        self._last_conversion_ = conversion
        high_pnl = low_pnl = 0.0
        for pos in self._positions_.values():
            if pos.NetPnL is None or pos.EntryPrice is None: continue
            current_price = bid if pos.IsLong else ask
            best_price = high_bid if pos.IsLong else low_ask
            worst_price = low_bid if pos.IsLong else high_ask
            entry_price = pos.EntryPrice.Price
            comm = pos.CommissionPnL.PnL if pos.CommissionPnL else 0.0
            swap = pos.SwapPnL.PnL if pos.SwapPnL else 0.0
            pnl_diff = calculate_pnl_difference(current_price, entry_price, pos.IsLong)
            if pos.GrossPnL: pos.GrossPnL.PnL = calculate_gross_pnl(pnl_diff, pos.Volume, conversion)
            pos.NetPnL.PnL = calculate_net_pnl(pos.GrossPnL.PnL if pos.GrossPnL else 0.0, comm, swap)
            if pos.EntryTimestamp:
                duration_sec = (timestamp - pos.EntryTimestamp.DateTime).total_seconds()
                pos.NetPnL.Duration = duration_sec if duration_sec > 0 else None
            if self._account_ and self._account_.Balance: pos.NetPnL.Reference = self._account_.Balance
            ref_balance = pos.NetPnL.Reference
            duration = pos.NetPnL.Duration
            contract = pos.Security.Contract if pos.Security else None
            best_pnl = calculate_net_pnl(calculate_gross_pnl(calculate_pnl_difference(best_price, entry_price, pos.IsLong), pos.Volume, conversion), comm, swap)
            worst_pnl = calculate_net_pnl(calculate_gross_pnl(calculate_pnl_difference(worst_price, entry_price, pos.IsLong), pos.Volume, conversion), comm, swap)
            high_pnl += best_pnl if pos.IsLong else worst_pnl
            low_pnl += worst_pnl if pos.IsLong else best_pnl
            if pos._max_equity_drawdown_price_ is None:
                pos._max_equity_drawdown_price_ = PriceAPI(Price=worst_price, Reference=entry_price, Contract=contract)
            elif (pos.IsLong and worst_price < pos._max_equity_drawdown_price_.Price) or (pos.IsShort and worst_price > pos._max_equity_drawdown_price_.Price):
                pos._max_equity_drawdown_price_.Price = worst_price
            if pos._max_equity_runup_price_ is None:
                pos._max_equity_runup_price_ = PriceAPI(Price=best_price, Reference=entry_price, Contract=contract)
            elif (pos.IsLong and best_price > pos._max_equity_runup_price_.Price) or (pos.IsShort and best_price < pos._max_equity_runup_price_.Price):
                pos._max_equity_runup_price_.Price = best_price
            if pos._max_equity_drawdown_pnl_ is None:
                pos._max_equity_drawdown_pnl_ = PnLAPI(PnL=worst_pnl, Reference=ref_balance, Duration=duration)
            elif worst_pnl < pos._max_equity_drawdown_pnl_.PnL:
                pos._max_equity_drawdown_pnl_.PnL = worst_pnl
                pos._max_equity_drawdown_pnl_.Reference = ref_balance
                pos._max_equity_drawdown_pnl_.Duration = duration
            if pos._max_equity_runup_pnl_ is None:
                pos._max_equity_runup_pnl_ = PnLAPI(PnL=best_pnl, Reference=ref_balance, Duration=duration)
            elif best_pnl > pos._max_equity_runup_pnl_.PnL:
                pos._max_equity_runup_pnl_.PnL = best_pnl
                pos._max_equity_runup_pnl_.Reference = ref_balance
                pos._max_equity_runup_pnl_.Duration = duration
        self._track_equity_()
        if not isinstance(data, TickAPI):
            self._equity_stamp_ = timestamp
            self._record_equity_()
            if timestamp != self._excursion_stamp_:
                self._excursion_stamp_ = timestamp
                base = self._account_.Balance if (self._account_ and self._account_.Balance is not None) else 0.0
                high, low = data.HighTick, data.LowTick
                if high is not None and low is not None and high.Timestamp is not None and low.Timestamp is not None and high.Timestamp.DateTime <= low.Timestamp.DateTime:
                    first, second = base + high_pnl, base + low_pnl
                else:
                    first, second = base + low_pnl, base + high_pnl
                self._accumulate_excursion_(first)
                self._accumulate_excursion_(second)
                self._accumulate_excursion_(self.Equity)

    def open_order(self, order: OrderAPI) -> None:
        self._orders_[order.UID] = order

    def modify_order(self, order: OrderAPI) -> None:
        if order.UID in self._orders_:
            self._orders_[order.UID] = order

    def close_order(self, order_uid: int) -> None:
        if order_uid in self._orders_:
            del self._orders_[order_uid]

    @staticmethod
    def _extend_price_(backing: Union[PriceAPI, None], price: float, rising: bool, falling: bool) -> None:
        if backing and ((falling and price < backing.Price) or (rising and price > backing.Price)): backing.Price = price

    @staticmethod
    def _extend_pnl_(backing: Union[PnLAPI, None], source: PnLAPI, pnl: float, rising: bool, falling: bool) -> None:
        if backing and ((falling and pnl < backing.PnL) or (rising and pnl > backing.PnL)):
            backing.PnL = pnl
            backing.Reference = source.Reference
            backing.Duration = source.Duration

    @staticmethod
    def _inherit_position_state_(src: PositionAPI, dst: PositionAPI) -> None:
        from Library.Portfolio.Trade import TradeAPI
        if dst._type_ is None: setattr(dst, 'Type', src.Type)
        if dst._direction_ is None: setattr(dst, 'Direction', src.Direction)
        if dst._security_ is None: setattr(dst, 'Security', src.Security)
        if dst._order_ is None: setattr(dst, 'Order', src.Order)
        if dst._entry_timestamp_ is None: setattr(dst, 'EntryTimestamp', src.EntryTimestamp)
        if dst._entry_price_ is None: setattr(dst, 'EntryPrice', src.EntryPrice)
        if isinstance(dst, TradeAPI):
            if dst._stop_loss_price_ is None: setattr(dst, 'StopLossPrice', src.StopLossPrice)
            if dst._take_profit_price_ is None: setattr(dst, 'TakeProfitPrice', src.TakeProfitPrice)
            if dst._stop_loss_pnl_ is None: setattr(dst, 'StopLossPnL', src.StopLossPnL)
            if dst._take_profit_pnl_ is None: setattr(dst, 'TakeProfitPnL', src.TakeProfitPnL)
        if dst._max_equity_drawdown_price_ is None: setattr(dst, 'MaxEquityDrawdownPrice', src.MaxEquityDrawdownPrice)
        if dst._max_equity_runup_price_ is None: setattr(dst, 'MaxEquityRunupPrice', src.MaxEquityRunupPrice)
        if dst._max_equity_drawdown_pnl_ is None: setattr(dst, 'MaxEquityDrawdownPnL', src.MaxEquityDrawdownPnL)
        if dst._max_equity_runup_pnl_ is None: setattr(dst, 'MaxEquityRunupPnL', src.MaxEquityRunupPnL)
        if dst._entry_balance_ is None: setattr(dst, 'EntryBalance', src.EntryBalance)
        if dst.Volume is None: dst.Volume = src.Volume
        if dst.Quantity is None: dst.Quantity = src.Quantity
        if dst.UsedMargin is None: dst.UsedMargin = src.UsedMargin
        if dst.MidBalance is None: dst.MidBalance = src.MidBalance
        if dst.Label is None: dst.Label = src.Label
        if dst.Comment is None: dst.Comment = src.Comment

    def _compute_target_pnl_(self, pos: PositionAPI, target_price: Union[float, None]) -> Union[float, None]:
        entry = pos.EntryPrice.Price if pos.EntryPrice else None
        if target_price is None or entry is None or pos.Volume is None: return None
        comm = pos.CommissionPnL.PnL if pos.CommissionPnL else 0.0
        swap = pos.SwapPnL.PnL if pos.SwapPnL else 0.0
        diff = calculate_pnl_difference(target_price, entry, pos.IsLong)
        return calculate_net_pnl(calculate_gross_pnl(diff, pos.Volume, self._last_conversion_), comm, swap)

    def _refresh_target_pnls_(self, pos: PositionAPI) -> None:
        sl_price = pos.StopLossPrice.Price if pos.StopLossPrice else None
        tp_price = pos.TakeProfitPrice.Price if pos.TakeProfitPrice else None
        sl_pnl = self._compute_target_pnl_(pos, sl_price)
        tp_pnl = self._compute_target_pnl_(pos, tp_price)
        if sl_pnl is not None:
            setattr(pos, 'StopLossPnL', sl_pnl)
        else:
            pos._stop_loss_pnl_ = None
        if tp_pnl is not None:
            setattr(pos, 'TakeProfitPnL', tp_pnl)
        else:
            pos._take_profit_pnl_ = None

    def open_position(self, order_uid: Union[int, None], position: PositionAPI) -> None:
        if order_uid is not None and order_uid in self._orders_:
            del self._orders_[order_uid]
        existing = self._positions_.get(position.UID)
        self._positions_[position.UID] = position
        if existing is not None:
            self._inherit_position_state_(existing, position)
            self._refresh_target_pnls_(position); return
        base = self._account_.Balance if self._account_ else 0.0
        setattr(position, 'EntryBalance', base)
        position.MidBalance = base
        self._refresh_target_pnls_(position)

    def modify_position(self, position: PositionAPI) -> None:
        if position.UID in self._positions_:
            old_pos = self._positions_[position.UID]
            self._inherit_position_state_(old_pos, position)
            self._positions_[position.UID] = position
            self._refresh_target_pnls_(position)

    def close_position(self, position_uid: int, position: Union[PositionAPI, None], trade: TradeAPI) -> None:
        if position_uid in self._positions_:
            old_pos = self._positions_[position_uid]
            self._inherit_position_state_(old_pos, trade)
            if trade._position_ is None: trade._position_ = old_pos
            setattr(trade, 'EntryBalance', old_pos.EntryBalance)
            if trade.ExitPrice and trade.ExitPrice.Price is not None:
                self._extend_price_(trade._max_equity_drawdown_price_, trade.ExitPrice.Price, trade.IsShort, trade.IsLong)
                self._extend_price_(trade._max_equity_runup_price_, trade.ExitPrice.Price, trade.IsLong, trade.IsShort)
            net = trade.NetPnL.PnL if (trade.NetPnL and trade.NetPnL.PnL is not None) else 0.0
            if trade.NetPnL:
                self._extend_pnl_(trade._max_equity_drawdown_pnl_, trade.NetPnL, net, False, True)
                self._extend_pnl_(trade._max_equity_runup_pnl_, trade.NetPnL, net, True, False)
            base = old_pos.MidBalance if old_pos.MidBalance is not None else (old_pos.EntryBalance or 0.0)
            new_mid = base + net
            old_pos.MidBalance = new_mid
            trade.MidBalance = new_mid
            setattr(trade, 'ExitBalance', new_mid)
            if self._account_: self._account_.Balance += net
            if position is not None:
                self._inherit_position_state_(old_pos, position)
                position.MidBalance = new_mid
                self._positions_[position_uid] = position
            else:
                del self._positions_[position_uid]
        self._trades_.append(trade)
        self._track_equity_()
        self._record_equity_()

    def calculate_statistics(self, start: datetime, stop: datetime) -> pl.DataFrame:
        from Library.Portfolio.Statistic import generate_net_report
        if not self._account_: return pl.DataFrame()
        return generate_net_report(self.Positions, self.Trades, self._account_, start, stop, self.EquityCurve, self.Excursions)

    @property
    def Account(self) -> Union[AccountAPI, None]:
        return self._account_

    @Account.setter
    def Account(self, account: Union[AccountAPI, None]) -> None:
        self._account_ = account
        if self._initial_balance_ is None and account is not None and account.Balance is not None:
            self._initial_balance_ = account.Balance

    @property
    def Security(self) -> Union[SecurityAPI, None]:
        return self._security_

    @Security.setter
    def Security(self, security: Union[SecurityAPI, None]) -> None:
        self._security_ = security

    def order(self, uid: int) -> Union[OrderAPI, None]:
        return self._orders_.get(uid)

    def position(self, uid: int) -> Union[PositionAPI, None]:
        return self._positions_.get(uid)

    def trade(self, uid: int) -> Union[TradeAPI, None]:
        return next((t for t in self._trades_ if t.UID == uid), None)

    @property
    def BuyOrders(self) -> list[OrderAPI]:
        return [o for o in self._orders_.values() if o.IsBuy]

    @property
    def SellOrders(self) -> list[OrderAPI]:
        return [o for o in self._orders_.values() if o.IsSell]

    @property
    def BuyPositions(self) -> list[PositionAPI]:
        return [p for p in self._positions_.values() if p.IsLong]

    @property
    def SellPositions(self) -> list[PositionAPI]:
        return [p for p in self._positions_.values() if p.IsShort]

    @property
    def BuyTrades(self) -> list[TradeAPI]:
        return [t for t in self._trades_ if t.IsLong]

    @property
    def SellTrades(self) -> list[TradeAPI]:
        return [t for t in self._trades_ if t.IsShort]

    @property
    def RealizedPnL(self) -> float:
        return sum((t.NetPnL.PnL or 0.0) for t in self._trades_ if t.NetPnL)

    @property
    def UnrealizedPnL(self) -> float:
        return sum((p.NetPnL.PnL or 0.0) for p in self._positions_.values() if p.NetPnL)

    @property
    def NetPnL(self) -> float:
        return self.RealizedPnL + self.UnrealizedPnL

    @property
    def Equity(self) -> float:
        balance = self._account_.Balance if self._account_ and self._account_.Balance is not None else 0.0
        return balance + self.UnrealizedPnL

    @property
    def InitialBalance(self) -> Union[float, None]:
        return self._initial_balance_

    @property
    def EquityPeak(self) -> Union[float, None]:
        return self._equity_peak_

    @property
    def EquityTrough(self) -> Union[float, None]:
        return self._equity_trough_

    @property
    def EquityDrawdown(self) -> float:
        return self.Equity / self._equity_peak_ - 1.0 if self._equity_peak_ else 0.0

    @property
    def EquityRunup(self) -> float:
        return self.Equity / self._equity_trough_ - 1.0 if self._equity_trough_ else 0.0

    @property
    def EquityCurve(self) -> list:
        return [equity for _, equity in self._equity_curve_]

    @property
    def EquityTrack(self) -> list:
        return list(self._equity_curve_)

    @property
    def MaxDrawdown(self) -> float:
        return self._max_drawdown_

    @property
    def MeanDrawdown(self) -> float:
        return self._drawdown_sum_ / self._excursion_count_ if self._excursion_count_ else 0.0

    @property
    def MaxRunup(self) -> float:
        return self._max_runup_

    @property
    def MeanRunup(self) -> float:
        return self._runup_sum_ / self._excursion_count_ if self._excursion_count_ else 0.0

    @property
    def Excursions(self) -> dict:
        count = self._excursion_count_ or 1
        return {
            "max_drawdown": self._max_drawdown_, "mean_drawdown": self.MeanDrawdown,
            "max_runup": self._max_runup_, "mean_runup": self.MeanRunup,
            "max_drawdown_value": self._max_drawdown_value_, "mean_drawdown_value": self._drawdown_value_sum_ / count,
            "max_runup_value": self._max_runup_value_, "mean_runup_value": self._runup_value_sum_ / count
        }

    @property
    def Direction(self) -> Direction:
        return calculate_direction(self.NetPnL)

    @property
    def Return(self) -> Union[float, None]:
        if not self._account_ or not self._account_.Balance: return None
        return calculate_pnl_return(self.NetPnL, self._account_.Balance)

    @property
    def LogReturn(self) -> Union[float, None]:
        return calculate_log_return(self.Return)

    @property
    def Percentage(self) -> Union[float, None]:
        return calculate_percentage(self.Return)

    @property
    def LogPercentage(self) -> Union[float, None]:
        return calculate_log_percentage(self.LogReturn)

    def _first_entry_(self) -> Union[datetime, None]:
        timestamps = [p.EntryTimestamp.DateTime for p in self._positions_.values() if p.EntryTimestamp]
        timestamps.extend(t.EntryTimestamp.DateTime for t in self._trades_ if t.EntryTimestamp)
        return min(timestamps) if timestamps else None

    def _duration_(self) -> Union[float, None]:
        first, last = self._first_entry_(), self._equity_stamp_
        if not first or last is None: return None
        return (last - first).total_seconds()

    @property
    def AnnualizedReturn(self) -> Union[float, None]:
        ret = self.Return
        if ret is None: return None
        duration = self._duration_()
        return calculate_annualized_return(ret, duration) if duration is not None else None

    @property
    def AnnualizedLogReturn(self) -> Union[float, None]:
        log_ret = self.LogReturn
        if log_ret is None: return None
        duration = self._duration_()
        return calculate_annualized_log_return(log_ret, duration) if duration is not None else None

    @property
    def AnnualizedPercentage(self) -> Union[float, None]:
        return calculate_percentage(self.AnnualizedReturn)

    @property
    def AnnualizedLogPercentage(self) -> Union[float, None]:
        return calculate_log_percentage(self.AnnualizedLogReturn)

    @staticmethod
    def _frame_(items) -> pl.DataFrame:
        if not items: return pl.DataFrame()
        return pl.DataFrame([item.dict() for item in items], strict=False)

    @property
    def Orders(self) -> pl.DataFrame:
        return self._frame_(self._orders_.values())

    @property
    def Positions(self) -> pl.DataFrame:
        return self._frame_(self._positions_.values())

    @property
    def Trades(self) -> pl.DataFrame:
        return self._frame_(self._trades_)

    @property
    def Deals(self) -> pl.DataFrame:
        from Library.Portfolio.Statistic import aggregate_trades
        if not self._trades_: return pl.DataFrame()
        return aggregate_trades(self.Trades)