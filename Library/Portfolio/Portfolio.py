from __future__ import annotations

from datetime import datetime
from dataclasses import dataclass, field
from typing import Union, ClassVar, TYPE_CHECKING

from Library.Database.Dataframe import pl
from Library.Database.Datapoint import DatapointAPI
from Library.Database.Query import QueryAPI
from Library.Market.Price import Direction, PriceAPI
from Library.Market.Tick import TickAPI
from Library.Portfolio.PnL import PnLAPI
from Library.Statistic.Curve import CurveAPI
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
from Library.Utility.Typing import MISSING

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
    _buy_realized_: float = field(default=0.0, init=False)
    _sell_realized_: float = field(default=0.0, init=False)
    _equity_peak_: Union[float, None] = field(default=None, init=False)
    _equity_trough_: Union[float, None] = field(default=None, init=False)
    _equity_stamp_: Union[datetime, None] = field(default=None, init=False)
    _excursion_stamp_: Union[datetime, None] = field(default=None, init=False)
    _equity_curve_: CurveAPI = field(default_factory=CurveAPI, init=False)
    _buy_equity_curve_: CurveAPI = field(default_factory=CurveAPI, init=False)
    _sell_equity_curve_: CurveAPI = field(default_factory=CurveAPI, init=False)
    _last_conversion_: float = field(default=1.0, init=False)

    def __post_init__(self,
                      db: Union[DatabaseAPI, None],
                      migrate: bool,
                      autoload: bool,
                      autooverload: bool,
                      autosave: bool) -> None:
        super().__post_init__(db=db, migrate=migrate, autoload=autoload, autooverload=autooverload, autosave=autosave)

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

    def init_data(self, account: AccountAPI, orders: list[OrderAPI] = MISSING, positions: list[PositionAPI] = MISSING, trades: list[TradeAPI] = MISSING) -> None:
        self._account_ = account
        if orders:
            for o in orders: self._orders_[o.UID] = o
        if positions:
            for p in positions: self._positions_[p.UID] = p
        if trades:
            self._trades_.extend(trades)
            for trade in trades: self._realize_(trade)
        balance = account.Balance if account and account.Balance is not None else 0.0
        self._initial_balance_ = balance - self._buy_realized_ - self._sell_realized_
        self._equity_peak_ = self.Equity
        self._equity_trough_ = self.Equity

    def _realize_(self, trade: TradeAPI) -> None:
        net = trade.NetPnL.PnL if trade.NetPnL and trade.NetPnL.PnL is not None else 0.0
        if trade.IsLong: self._buy_realized_ += net
        elif trade.IsShort: self._sell_realized_ += net

    def _track_equity_(self, equity: float) -> None:
        if self._equity_peak_ is None or equity > self._equity_peak_: self._equity_peak_ = equity
        if self._equity_trough_ is None or equity < self._equity_trough_: self._equity_trough_ = equity

    def _record_equity_(self, equity: float) -> None:
        if self._equity_stamp_ is None: return
        origin = self._initial_balance_ or 0.0
        self._equity_curve_.record(self._equity_stamp_, equity)
        self._buy_equity_curve_.record(self._equity_stamp_, origin + self._buy_realized_ + self.BuyUnrealizedPnL)
        self._sell_equity_curve_.record(self._equity_stamp_, origin + self._sell_realized_ + self.SellUnrealizedPnL)

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
        buy_pnl = buy_high_pnl = buy_low_pnl = 0.0
        sell_pnl = sell_high_pnl = sell_low_pnl = 0.0
        balance = self._account_.Balance if self._account_ else None
        for pos in self._positions_.values():
            net, entry = pos.NetPnL, pos.EntryPrice
            if net is None or entry is None: continue
            is_long, is_short = pos.IsLong, pos.IsShort
            gross, commission, swapped, opened, volume = pos.GrossPnL, pos.CommissionPnL, pos.SwapPnL, pos.EntryTimestamp, pos.Volume
            current_price = bid if is_long else ask
            best_price = high_bid if is_long else low_ask
            worst_price = low_bid if is_long else high_ask
            entry_price = entry.Price
            comm = commission.PnL if commission else 0.0
            swap = swapped.PnL if swapped else 0.0
            pnl_diff = calculate_pnl_difference(current_price, entry_price, is_long)
            if gross: gross.PnL = calculate_gross_pnl(pnl_diff, volume, conversion)
            net.PnL = calculate_net_pnl(gross.PnL if gross else 0.0, comm, swap)
            if opened:
                duration_sec = (timestamp - opened.DateTime).total_seconds()
                net.Duration = duration_sec if duration_sec > 0 else None
            if balance: net.Reference = balance
            ref_balance, duration = net.Reference, net.Duration
            best_pnl = calculate_net_pnl(calculate_gross_pnl(calculate_pnl_difference(best_price, entry_price, is_long), volume, conversion), comm, swap)
            worst_pnl = calculate_net_pnl(calculate_gross_pnl(calculate_pnl_difference(worst_price, entry_price, is_long), volume, conversion), comm, swap)
            if is_long:
                high_pnl += best_pnl
                low_pnl += worst_pnl
                buy_pnl += net.PnL
                buy_high_pnl += best_pnl
                buy_low_pnl += worst_pnl
            else:
                high_pnl += worst_pnl
                low_pnl += best_pnl
                if is_short:
                    sell_pnl += net.PnL
                    sell_high_pnl += worst_pnl
                    sell_low_pnl += best_pnl
            drawdown_price, runup_price = pos._max_equity_drawdown_price_, pos._max_equity_runup_price_
            if drawdown_price is None:
                pos._max_equity_drawdown_price_ = PriceAPI(Price=worst_price, Reference=entry_price, Contract=pos.Security.Contract if pos.Security else None)
            elif (is_long and worst_price < drawdown_price.Price) or (is_short and worst_price > drawdown_price.Price):
                drawdown_price.Price = worst_price
            if runup_price is None:
                pos._max_equity_runup_price_ = PriceAPI(Price=best_price, Reference=entry_price, Contract=pos.Security.Contract if pos.Security else None)
            elif (is_long and best_price > runup_price.Price) or (is_short and best_price < runup_price.Price):
                runup_price.Price = best_price
            drawdown_pnl, runup_pnl = pos._max_equity_drawdown_pnl_, pos._max_equity_runup_pnl_
            if drawdown_pnl is None:
                pos._max_equity_drawdown_pnl_ = PnLAPI(PnL=worst_pnl, Reference=ref_balance, Duration=duration)
            elif worst_pnl < drawdown_pnl.PnL:
                drawdown_pnl.PnL = worst_pnl
                drawdown_pnl.Reference = ref_balance
                drawdown_pnl.Duration = duration
            if runup_pnl is None:
                pos._max_equity_runup_pnl_ = PnLAPI(PnL=best_pnl, Reference=ref_balance, Duration=duration)
            elif best_pnl > runup_pnl.PnL:
                runup_pnl.PnL = best_pnl
                runup_pnl.Reference = ref_balance
                runup_pnl.Duration = duration
        equity = self.Equity
        self._track_equity_(equity)
        if isinstance(data, TickAPI): return
        self._equity_stamp_ = timestamp
        origin = self._initial_balance_ or 0.0
        buy_base, sell_base = origin + self._buy_realized_, origin + self._sell_realized_
        self._equity_curve_.record(timestamp, equity)
        self._buy_equity_curve_.record(timestamp, buy_base + buy_pnl)
        self._sell_equity_curve_.record(timestamp, sell_base + sell_pnl)
        if timestamp == self._excursion_stamp_: return
        self._excursion_stamp_ = timestamp
        base = self._account_.Balance if (self._account_ and self._account_.Balance is not None) else 0.0
        high, low = data.HighTick, data.LowTick
        if high is not None and low is not None and high.Timestamp is not None and low.Timestamp is not None and high.Timestamp.DateTime <= low.Timestamp.DateTime:
            self._equity_curve_.observe(base + high_pnl, base + low_pnl, equity)
            self._buy_equity_curve_.observe(buy_base + buy_high_pnl, buy_base + buy_low_pnl, buy_base + buy_pnl)
            self._sell_equity_curve_.observe(sell_base + sell_high_pnl, sell_base + sell_low_pnl, sell_base + sell_pnl)
        else:
            self._equity_curve_.observe(base + low_pnl, base + high_pnl, equity)
            self._buy_equity_curve_.observe(buy_base + buy_low_pnl, buy_base + buy_high_pnl, buy_base + buy_pnl)
            self._sell_equity_curve_.observe(sell_base + sell_low_pnl, sell_base + sell_high_pnl, sell_base + sell_pnl)

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
            self._realize_(trade)
            if position is not None:
                self._inherit_position_state_(old_pos, position)
                position.MidBalance = new_mid
                self._positions_[position_uid] = position
            else:
                del self._positions_[position_uid]
        self._trades_.append(trade)
        equity = self.Equity
        self._track_equity_(equity)
        self._record_equity_(equity)

    def calculate_statistics(self, start: datetime = MISSING, stop: datetime = MISSING) -> pl.DataFrame:
        from Library.Portfolio.Statistic import generate_net_report
        if not self._account_: return pl.DataFrame()
        start = start or self._equity_curve_.Start
        stop = stop or self._equity_curve_.Stop
        if not start or not stop: return pl.DataFrame()
        return generate_net_report(self.Positions, self.Trades, self._account_, start, stop, (self._buy_equity_curve_, self._sell_equity_curve_, self._equity_curve_))

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
    def RiskFree(self) -> float:
        return self._equity_curve_.RiskFree

    @RiskFree.setter
    def RiskFree(self, risk_free: float) -> None:
        self._equity_curve_.RiskFree = risk_free
        self._buy_equity_curve_.RiskFree = risk_free
        self._sell_equity_curve_.RiskFree = risk_free

    @property
    def BuyRealizedPnL(self) -> float:
        return self._buy_realized_

    @property
    def SellRealizedPnL(self) -> float:
        return self._sell_realized_

    @property
    def RealizedPnL(self) -> float:
        return self._buy_realized_ + self._sell_realized_

    @property
    def BuyUnrealizedPnL(self) -> float:
        return sum((p.NetPnL.PnL or 0.0) for p in self._positions_.values() if p.NetPnL and p.IsLong)

    @property
    def SellUnrealizedPnL(self) -> float:
        return sum((p.NetPnL.PnL or 0.0) for p in self._positions_.values() if p.NetPnL and p.IsShort)

    @property
    def UnrealizedPnL(self) -> float:
        return sum((p.NetPnL.PnL or 0.0) for p in self._positions_.values() if p.NetPnL)

    @property
    def BuyNetPnL(self) -> float:
        return self._buy_realized_ + self.BuyUnrealizedPnL

    @property
    def SellNetPnL(self) -> float:
        return self._sell_realized_ + self.SellUnrealizedPnL

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
    def BuyEquityCurve(self) -> CurveAPI:
        return self._buy_equity_curve_

    @property
    def SellEquityCurve(self) -> CurveAPI:
        return self._sell_equity_curve_

    @property
    def EquityCurve(self) -> CurveAPI:
        return self._equity_curve_

    @property
    def Direction(self) -> Direction:
        return Direction.calculate(self.NetPnL)

    @property
    def Return(self) -> Union[float, None]:
        return calculate_pnl_return(self.NetPnL, self._initial_balance_)

    @property
    def LogReturn(self) -> Union[float, None]:
        return calculate_log_return(self.Return)

    @property
    def Percentage(self) -> Union[float, None]:
        return calculate_percentage(self.Return)

    @property
    def LogPercentage(self) -> Union[float, None]:
        return calculate_log_percentage(self.LogReturn)

    @property
    def AnnualizedReturn(self) -> Union[float, None]:
        ret = self.Return
        return calculate_annualized_return(ret, self._equity_curve_.Duration) if ret is not None else None

    @property
    def AnnualizedLogReturn(self) -> Union[float, None]:
        log_ret = self.LogReturn
        return calculate_annualized_log_return(log_ret, self._equity_curve_.Duration) if log_ret is not None else None

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