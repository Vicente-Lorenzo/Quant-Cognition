from __future__ import annotations

import math
from datetime import date, timedelta, datetime
from typing import Union, TYPE_CHECKING

from Library.Database.Dataframe import pl
from Library.Market.Price import Direction
from Library.Portfolio.Order import OrderAPI
from Library.Portfolio.Position import PositionAPI
from Library.Portfolio.Trade import TradeAPI

if TYPE_CHECKING:
    from Library.Portfolio.Account import AccountAPI

def calculate_log_value(value: float) -> Union[float, None]:
    if not value or value <= 0.0: return None
    return math.log(value)

def calculate_price_return(price: float, reference: float) -> Union[float, None]:
    if not reference: return None
    return (price / reference) - 1.0

def calculate_pnl_return(pnl: float, reference: float) -> Union[float, None]:
    if not reference: return None
    return pnl / reference

def calculate_log_return(ret: float) -> Union[float, None]:
    if ret is None or ret <= -1.0: return None
    return math.log1p(ret)

def calculate_percentage(ret: float) -> Union[float, None]:
    if ret is None: return None
    return ret * 100.0

def calculate_log_percentage(log_ret: float) -> Union[float, None]:
    if log_ret is None: return None
    return log_ret * 100.0

def calculate_direction(value: float) -> Direction:
    return Direction.Buy if value > 0 else Direction.Sell if value < 0 else Direction.Neutral

def calculate_duration_seconds(start: date, stop: date) -> float:
    if not start or not stop: return 0.0
    return (stop - start).days * 86400.0

def calculate_annualized_return(ret: float, duration_seconds: float, trading_days: int = 365, pct: bool = False) -> float:
    if not ret or not duration_seconds or duration_seconds <= 0.0: return 0.0
    ret = ret / 100.0 if pct else ret
    value = ((1.0 + ret) ** ((trading_days * 86400.0) / duration_seconds)) - 1.0
    return calculate_percentage(value) if pct else value

def calculate_annualized_log_return(log_ret: float, duration_seconds: float, trading_days: int = 365) -> float:
    if log_ret is None or not duration_seconds or duration_seconds <= 0.0: return 0.0
    return log_ret * ((trading_days * 86400.0) / duration_seconds)

def calculate_pnl_difference(current_price: float, entry_price: float, is_long: bool) -> float:
    return (current_price - entry_price) if is_long else (entry_price - current_price)

def calculate_gross_pnl(pnl_diff: float, volume: float, conversion: float = 1.0) -> float:
    return pnl_diff * volume * conversion

def calculate_net_pnl(gross_pnl: float, commission_pnl: float, swap_pnl: float) -> float:
    return gross_pnl + commission_pnl + swap_pnl


STATISTICS_METRICS_LABEL = "Statistical Metrics"

REALIZED_BUY_INDIVIDUAL = "Realized Buy Metrics (Individual)"
REALIZED_SELL_INDIVIDUAL = "Realized Sell Metrics (Individual)"
REALIZED_TOTAL_INDIVIDUAL = "Realized Total Metrics (Individual)"
REALIZED_BUY_AGGREGATED = "Realized Buy Metrics (Aggregated)"
REALIZED_SELL_AGGREGATED = "Realized Sell Metrics (Aggregated)"
REALIZED_TOTAL_AGGREGATED = "Realized Total Metrics (Aggregated)"

UNREALIZED_BUY_INDIVIDUAL = "Unrealized Buy Metrics (Individual)"
UNREALIZED_SELL_INDIVIDUAL = "Unrealized Sell Metrics (Individual)"
UNREALIZED_TOTAL_INDIVIDUAL = "Unrealized Total Metrics (Individual)"
UNREALIZED_BUY_AGGREGATED = "Unrealized Buy Metrics (Aggregated)"
UNREALIZED_SELL_AGGREGATED = "Unrealized Sell Metrics (Aggregated)"
UNREALIZED_TOTAL_AGGREGATED = "Unrealized Total Metrics (Aggregated)"

NET_BUY_INDIVIDUAL = "Net Buy Metrics (Individual)"
NET_SELL_INDIVIDUAL = "Net Sell Metrics (Individual)"
NET_TOTAL_INDIVIDUAL = "Net Total Metrics (Individual)"
NET_BUY_AGGREGATED = "Net Buy Metrics (Aggregated)"
NET_SELL_AGGREGATED = "Net Sell Metrics (Aggregated)"
NET_TOTAL_AGGREGATED = "Net Total Metrics (Aggregated)"

TOTALTRADESVALUE = "Nr Total of Trades"
TOTALPOINTSVALUE = "Total Points"
TOTALPIPSVALUE = "Total Pips"

WINNINGTRADESVALUE = "Nr of Winning Trades"
WINNINGPOINTSVALUE = "Winning Points"
WINNINGPIPSVALUE = "Winning Pips"
WINNINGRATEPERC = "Winning Rate (%)"
MAXWINNINGTRADE = "Max Winning Trade"
AVERAGEWINNINGTRADE = "Avg Winning Trade"
MINWINNINGTRADE = "Min Winning Trade"
MAXWINNINGPOINTS = "Max Winning Points"
AVERAGEWINNINGPOINTS = "Avg Winning Points"
MINWINNINGPOINTS = "Min Winning Points"
MAXWINNINGPIPS = "Max Winning Pips"
AVERAGEWINNINGPIPS = "Avg Winning Pips"
MINWINNINGPIPS = "Min Winning Pips"
MAXWINNINGSTREAK = "Max Winning Streak"
EXPECTEDWINNINGRETURNPERC = "Expected Winning Return (%)"
WINNINGRETURNPERC = "Winning Return (%)"
WINNINGRETURNANNPERC = "Winning Return Annualized (%) [µ_up]"
WINNINGVOLATILITYPERC = "Winning Volatility (%)"
WINNINGVOLATILITYANNPERC = "Winning Volatility Annualized (%) [σ_up]"

LOSINGTRADESVALUE = "Nr of Losing Trades"
LOSINGPOINTSVALUE = "Losing Points"
LOSINGPIPSVALUE = "Losing Pips"
LOSINGRATEPERC = "Losing Rate (%)"
MAXLOSINGTRADE = "Max Losing Trade"
AVERAGELOSINGTRADE = "Avg Losing Trade"
MINLOSINGTRADE = "Min Losing Trade"
MAXLOSINGPOINTS = "Max Losing Points"
AVERAGELOSINGPOINTS = "Avg Losing Points"
MINLOSINGPOINTS = "Min Losing Points"
MAXLOSINGPIPS = "Max Losing Pips"
AVERAGELOSINGPIPS = "Avg Losing Pips"
MINLOSINGPIPS = "Min Losing Pips"
MAXLOSINGSTREAK = "Max Losing Streak"
EXPECTEDLOSINGRETURNPERC = "Expected Losing Return (%)"
LOSINGRETURNPERC = "Losing Return (%)"
LOSINGRETURNANNPERC = "Losing Return Annualized (%) [µ_down]"
LOSINGVOLATILITYPERC = "Losing Volatility (%)"
LOSINGVOLATILITYANNPERC = "Losing Volatility Annualized (%) [σ_down]"

AVERAGETRADE = "Average Trade [Backward]"
AVERAGEPOINTS = "Average Points [Backward]"
AVERAGEPIPS = "Average Pips [Backward]"
EXPECTEDTRADE = "Expected Trade [Forward]"
EXPECTEDPOINTS = "Expected Points [Forward]"
EXPECTEDPIPS = "Expected Pips [Forward]"

GROSSPNLVALUE = "Gross Profit/Loss"
COMMISSIONSPNLVALUE = "Commissions Profit/Loss"
SWAPSPNLVALUE = "Swaps Profit/Loss"
NETPNLVALUE = "Net Profit/Loss"
EXPECTEDNETRETURNPERC = "Expected Net Return (%)"
NETRETURNPERC = "Net Return (%)"
NETRETURNANNPERC = "Net Return Annualized (%) [µ]"
UPSIDEVOLATILITYPERC = "Upside Volatility (%)"
UPSIDEVOLATILITYANNPERC = "Upside Volatility Annualized (%) [σ+]"
DOWNSIDEVOLATILITYPERC = "Downside Volatility (%)"
DOWNSIDEVOLATILITYANNPERC = "Downside Volatility Annualized (%) [σ-]"
NETVOLATILITYPERC = "Net Volatility (%)"
NETVOLATILITYANNPERC = "Net Volatility Annualized (%) [σ]"

PROFITFACTOR = "Profit Factor"
RISKTOREWARDRATIO = "Risk-to-Reward Ratio"
MAXBALANCEDRAWDOWNVALUE = "Max Balance Drawdown"
MAXBALANCEDRAWDOWNPERC = "Max Balance Drawdown (%)"
MEANBALANCEDRAWDOWNVALUE = "Mean Balance Drawdown"
MEANBALANCEDRAWDOWNPERC = "Mean Balance Drawdown (%)"
MAXBALANCERUNUPVALUE = "Max Balance Runup"
MAXBALANCERUNUPPERC = "Max Balance Runup (%)"
MEANBALANCERUNUPVALUE = "Mean Balance Runup"
MEANBALANCERUNUPPERC = "Mean Balance Runup (%)"
MAXEQUITYDRAWDOWNVALUE = "Max Equity Drawdown"
MAXEQUITYDRAWDOWNPERC = "Max Equity Drawdown (%)"
MEANEQUITYDRAWDOWNVALUE = "Mean Equity Drawdown"
MEANEQUITYDRAWDOWNPERC = "Mean Equity Drawdown (%)"
MAXEQUITYRUNUPVALUE = "Max Equity Runup"
MAXEQUITYRUNUPPERC = "Max Equity Runup (%)"
MEANEQUITYRUNUPVALUE = "Mean Equity Runup"
MEANEQUITYRUNUPPERC = "Mean Equity Runup (%)"
MAXHOLDINGTIME = "Max Holding Time (Days)"
AVERAGEHOLDINGTIME = "Avg Holding Time (Days)"
MINHOLDINGTIME = "Min Holding Time (Days)"
SHARPERATIO = "Sharpe Ratio Annualized"
SORTINORATIO = "Sortino Ratio Annualized"
CALMARRATIO = "Calmar Ratio Annualized"
STERLINGRATIO = "Sterling Ratio Annualized"

Metrics = [
    TOTALTRADESVALUE,
    TOTALPOINTSVALUE,
    TOTALPIPSVALUE,

    WINNINGTRADESVALUE,
    WINNINGPOINTSVALUE,
    WINNINGPIPSVALUE,
    WINNINGRATEPERC,
    MAXWINNINGTRADE,
    AVERAGEWINNINGTRADE,
    MINWINNINGTRADE,
    MAXWINNINGPOINTS,
    AVERAGEWINNINGPOINTS,
    MINWINNINGPOINTS,
    MAXWINNINGPIPS,
    AVERAGEWINNINGPIPS,
    MINWINNINGPIPS,
    MAXWINNINGSTREAK,
    EXPECTEDWINNINGRETURNPERC,
    WINNINGRETURNPERC,
    WINNINGRETURNANNPERC,
    WINNINGVOLATILITYPERC,
    WINNINGVOLATILITYANNPERC,

    LOSINGTRADESVALUE,
    LOSINGPOINTSVALUE,
    LOSINGPIPSVALUE,
    LOSINGRATEPERC,
    MAXLOSINGTRADE,
    AVERAGELOSINGTRADE,
    MINLOSINGTRADE,
    MAXLOSINGPOINTS,
    AVERAGELOSINGPOINTS,
    MINLOSINGPOINTS,
    MAXLOSINGPIPS,
    AVERAGELOSINGPIPS,
    MINLOSINGPIPS,
    MAXLOSINGSTREAK,
    EXPECTEDLOSINGRETURNPERC,
    LOSINGRETURNPERC,
    LOSINGRETURNANNPERC,
    LOSINGVOLATILITYPERC,
    LOSINGVOLATILITYANNPERC,

    AVERAGETRADE,
    AVERAGEPOINTS,
    AVERAGEPIPS,
    EXPECTEDTRADE,
    EXPECTEDPOINTS,
    EXPECTEDPIPS,

    GROSSPNLVALUE,
    COMMISSIONSPNLVALUE,
    SWAPSPNLVALUE,
    NETPNLVALUE,
    EXPECTEDNETRETURNPERC,
    NETRETURNPERC,
    NETRETURNANNPERC,
    UPSIDEVOLATILITYPERC,
    UPSIDEVOLATILITYANNPERC,
    DOWNSIDEVOLATILITYPERC,
    DOWNSIDEVOLATILITYANNPERC,
    NETVOLATILITYPERC,
    NETVOLATILITYANNPERC,

    PROFITFACTOR,
    RISKTOREWARDRATIO,
    MAXBALANCEDRAWDOWNVALUE,
    MAXBALANCEDRAWDOWNPERC,
    MEANBALANCEDRAWDOWNVALUE,
    MEANBALANCEDRAWDOWNPERC,
    MAXBALANCERUNUPVALUE,
    MAXBALANCERUNUPPERC,
    MEANBALANCERUNUPVALUE,
    MEANBALANCERUNUPPERC,
    MAXEQUITYDRAWDOWNVALUE,
    MAXEQUITYDRAWDOWNPERC,
    MEANEQUITYDRAWDOWNVALUE,
    MEANEQUITYDRAWDOWNPERC,
    MAXEQUITYRUNUPVALUE,
    MAXEQUITYRUNUPPERC,
    MEANEQUITYRUNUPVALUE,
    MEANEQUITYRUNUPPERC,
    MAXHOLDINGTIME,
    AVERAGEHOLDINGTIME,
    MINHOLDINGTIME,
    SHARPERATIO,
    SORTINORATIO,
    CALMARRATIO,
    STERLINGRATIO
]

OrderView = {
    str(OrderAPI.ID.UID): pl.Int64(),
    str(OrderAPI.ID.Position): pl.Int64(),
    str(OrderAPI.ID.Direction): pl.String(),
    str(OrderAPI.ID.OrderType): pl.String(),
    str(OrderAPI.ID.OrderStatus): pl.String(),
    str(OrderAPI.ID.Volume): pl.Float64(),
    str(OrderAPI.ID.ExecutedVolume): pl.Float64(),
    str(OrderAPI.ID.EntryTimestamp): pl.Datetime(),
    str(OrderAPI.ID.ExpirationTimestamp): pl.Datetime(),
    str(OrderAPI.ID.ExecutionPrice): pl.Float64(),
    str(OrderAPI.ID.LimitPrice): pl.Float64(),
    str(OrderAPI.ID.StopPrice): pl.Float64(),
    str(OrderAPI.ID.StopLossPrice): pl.Float64(),
    str(OrderAPI.ID.TakeProfitPrice): pl.Float64()
}

PositionView = {
    str(PositionAPI.ID.UID): pl.Int64(),
    str(PositionAPI.ID.Direction): pl.String(),
    str(PositionAPI.ID.Volume): pl.Float64(),
    str(PositionAPI.ID.Quantity): pl.Float64(),
    str(PositionAPI.ID.EntryTimestamp): pl.Datetime(),
    str(PositionAPI.ID.EntryPrice): pl.Float64(),
    str(PositionAPI.ID.ExitPrice): pl.Float64(),
    str(PositionAPI.ID.EntryBalance): pl.Float64(),
    str(PositionAPI.ID.MidBalance): pl.Float64(),
    str(PositionAPI.ID.Points): pl.Float64(),
    str(PositionAPI.ID.MaxEquityDrawdownPoints): pl.Float64(),
    str(PositionAPI.ID.MaxEquityRunupPoints): pl.Float64(),
    str(PositionAPI.ID.Return): pl.Float64(),
    str(PositionAPI.ID.MaxEquityDrawdownReturn): pl.Float64(),
    str(PositionAPI.ID.MaxEquityRunupReturn): pl.Float64(),
    str(PositionAPI.ID.RiskAdjustedReturn): pl.Float64(),
    str(PositionAPI.ID.GrossPnL): pl.Float64(),
    str(PositionAPI.ID.CommissionPnL): pl.Float64(),
    str(PositionAPI.ID.SwapPnL): pl.Float64(),
    str(PositionAPI.ID.NetPnL): pl.Float64()
}

TradeView = {
    str(TradeAPI.ID.UID): pl.Int64(),
    str(TradeAPI.ID.Position): pl.Int64(),
    str(TradeAPI.ID.Direction): pl.String(),
    str(TradeAPI.ID.Volume): pl.Float64(),
    str(TradeAPI.ID.EntryTimestamp): pl.Datetime(),
    str(TradeAPI.ID.ExitTimestamp): pl.Datetime(),
    str(TradeAPI.ID.EntryPrice): pl.Float64(),
    str(TradeAPI.ID.ExitPrice): pl.Float64(),
    str(TradeAPI.ID.EntryBalance): pl.Float64(),
    str(TradeAPI.ID.MidBalance): pl.Float64(),
    str(TradeAPI.ID.ExitBalance): pl.Float64(),
    str(TradeAPI.ID.Points): pl.Float64(),
    str(TradeAPI.ID.MaxEquityDrawdownPoints): pl.Float64(),
    str(TradeAPI.ID.MaxEquityRunupPoints): pl.Float64(),
    str(TradeAPI.ID.Return): pl.Float64(),
    str(TradeAPI.ID.MaxEquityDrawdownReturn): pl.Float64(),
    str(TradeAPI.ID.MaxEquityRunupReturn): pl.Float64(),
    str(TradeAPI.ID.RiskAdjustedReturn): pl.Float64(),
    str(TradeAPI.ID.GrossPnL): pl.Float64(),
    str(TradeAPI.ID.CommissionPnL): pl.Float64(),
    str(TradeAPI.ID.SwapPnL): pl.Float64(),
    str(TradeAPI.ID.NetPnL): pl.Float64()
}

DealView = {
    str(TradeAPI.ID.Position): pl.Int64(),
    str(TradeAPI.ID.UID): pl.List(pl.Int64),
    str(TradeAPI.ID.Direction): pl.String(),
    str(TradeAPI.ID.Volume): pl.Float64(),
    str(TradeAPI.ID.EntryTimestamp): pl.Datetime(),
    str(TradeAPI.ID.ExitTimestamp): pl.Datetime(),
    str(TradeAPI.ID.EntryPrice): pl.Float64(),
    str(TradeAPI.ID.ExitPrice): pl.Float64(),
    str(TradeAPI.ID.EntryBalance): pl.Float64(),
    str(TradeAPI.ID.MidBalance): pl.Float64(),
    str(TradeAPI.ID.ExitBalance): pl.Float64(),
    str(TradeAPI.ID.Points): pl.Float64(),
    str(TradeAPI.ID.MaxEquityDrawdownPoints): pl.Float64(),
    str(TradeAPI.ID.MaxEquityRunupPoints): pl.Float64(),
    str(TradeAPI.ID.Return): pl.Float64(),
    str(TradeAPI.ID.MaxEquityDrawdownReturn): pl.Float64(),
    str(TradeAPI.ID.MaxEquityRunupReturn): pl.Float64(),
    str(TradeAPI.ID.RiskAdjustedReturn): pl.Float64(),
    str(TradeAPI.ID.GrossPnL): pl.Float64(),
    str(TradeAPI.ID.CommissionPnL): pl.Float64(),
    str(TradeAPI.ID.SwapPnL): pl.Float64(),
    str(TradeAPI.ID.NetPnL): pl.Float64()
}

def reporting_view(df: pl.DataFrame, schema: dict) -> pl.DataFrame:
    if df.is_empty(): return pl.DataFrame(schema=schema)
    return df.select([col for col in schema if col in df.columns])

def order_view(df: pl.DataFrame) -> pl.DataFrame:
    return reporting_view(df, OrderView)

def position_view(df: pl.DataFrame) -> pl.DataFrame:
    return reporting_view(df, PositionView)

def trade_view(df: pl.DataFrame) -> pl.DataFrame:
    return reporting_view(df, TradeView)

def deal_view(df: pl.DataFrame) -> pl.DataFrame:
    return reporting_view(df, DealView)

def sort_items(df: pl.DataFrame) -> pl.DataFrame:
    entry_ts = str(PositionAPI.ID.EntryTimestamp)
    if df.is_empty() or entry_ts not in df.columns: return df
    return df.sort(by=entry_ts, descending=False)

def aggregate_items(df: pl.DataFrame) -> pl.DataFrame:
    position = str(TradeAPI.ID.Position)
    if df.is_empty() or position not in df.columns: return df
    volume = str(PositionAPI.ID.Volume)
    def _take_(col: str, op):
        return op(pl.col(col)) if col in df.columns else pl.lit(0.0).alias(col)
    def _weighted_(col: str):
        return ((pl.col(col) * pl.col(volume)).sum() / pl.col(volume).sum()).alias(col) if col in df.columns else pl.lit(0.0).alias(col)
    agg_exprs = [
        pl.col(str(PositionAPI.ID.UID)),
        pl.col(str(PositionAPI.ID.Direction)).first(),
        pl.col(str(PositionAPI.ID.EntryTimestamp)).min(),
        pl.col(str(PositionAPI.ID.EntryPrice)).first(),
        pl.col(volume).sum(),
        _weighted_(str(PositionAPI.ID.Points)),
        _weighted_(str(PositionAPI.ID.Pips)),
        _take_(str(PositionAPI.ID.GrossPnL), lambda x: x.sum()),
        _take_(str(PositionAPI.ID.CommissionPnL), lambda x: x.sum()),
        _take_(str(PositionAPI.ID.SwapPnL), lambda x: x.sum()),
        _take_(str(PositionAPI.ID.NetPnL), lambda x: x.sum()),
        _take_(str(PositionAPI.ID.MaxEquityDrawdownPoints), lambda x: x.min()),
        _take_(str(PositionAPI.ID.MaxEquityDrawdownPips), lambda x: x.min()),
        _take_(str(PositionAPI.ID.MaxEquityRunupPoints), lambda x: x.max()),
        _take_(str(PositionAPI.ID.MaxEquityRunupPips), lambda x: x.max()),
        _take_(str(PositionAPI.ID.Return), lambda x: x.sum()),
        _take_(str(PositionAPI.ID.LogReturn), lambda x: x.sum()),
        _take_(str(PositionAPI.ID.MaxEquityDrawdownReturn), lambda x: x.min()),
        _take_(str(PositionAPI.ID.MaxEquityRunupReturn), lambda x: x.max()),
        _take_(str(PositionAPI.ID.RiskAdjustedReturn), lambda x: x.sum()),
        _take_(str(PositionAPI.ID.EntryBalance), lambda x: x.first()),
        _take_(str(PositionAPI.ID.MidBalance), lambda x: x.last()),
    ]
    exit_ts = str(TradeAPI.ID.ExitTimestamp)
    if exit_ts in df.columns:
        agg_exprs.extend([
            pl.col(exit_ts).max(),
            pl.col(str(TradeAPI.ID.ExitPrice)).last(),
            _take_(str(TradeAPI.ID.ExitBalance), lambda x: x.last()),
        ])
    return df.group_by(position).agg(agg_exprs)

def aggregate_trades(df: pl.DataFrame) -> pl.DataFrame:
    return sort_items(aggregate_items(df))

def split_buy_sell(df: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame]:
    direction = str(PositionAPI.ID.Direction)
    if df.is_empty() or direction not in df.columns: return df, df
    return (df.filter(pl.col(direction) == Direction.Buy.name),
            df.filter(pl.col(direction) == Direction.Sell.name))

def split_winning_losing(df: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame]:
    net_pnl = str(PositionAPI.ID.NetPnL)
    if df.is_empty() or net_pnl not in df.columns: return df, df
    return (df.filter(pl.col(net_pnl) > 0),
            df.filter(pl.col(net_pnl) <= 0))

def calculate_total(df: pl.DataFrame) -> int:
    return df.shape[0] if not df.is_empty() else 0

def calculate_rate_perc(nr_cases: int, nr_total: int) -> float:
    return (nr_cases / nr_total) * 100.0 if nr_total else 0.0

def calculate_min_avg_max(nr_items: int, df: pl.DataFrame, column: str) -> tuple[float, float, float]:
    if nr_items > 0 and column in df.columns:
        return df[column].max(), df[column].mean(), df[column].min()
    return 0.0, 0.0, 0.0

def calculate_sum(df: pl.DataFrame, column: str) -> float:
    return df[column].sum() if not df.is_empty() and column in df.columns else 0.0

def calculate_average(net_value: float, nr_items: int) -> float:
    return net_value / nr_items if nr_items else 0.0

def calculate_expected(winning_perc: float, avg_win: float, losing_perc: float, avg_loss: float) -> float:
    return (winning_perc / 100.0 * avg_win) - (losing_perc / 100.0 * abs(avg_loss))

def calculate_return(df: pl.DataFrame) -> tuple[float, float]:
    log_ret = str(PositionAPI.ID.LogReturn)
    if df.is_empty() or log_ret not in df.columns: return 0.0, 0.0
    exp_log = df[log_ret].mean()
    tot_log = df[log_ret].sum()
    exp_ret_pct = (math.exp(exp_log) - 1.0) * 100.0 if exp_log else 0.0
    tot_ret_pct = (math.exp(tot_log) - 1.0) * 100.0 if tot_log else 0.0
    return exp_ret_pct, tot_ret_pct


def calculate_volatility(df: pl.DataFrame, upside: bool = False, downside: bool = False) -> float:
    log_ret = str(PositionAPI.ID.LogReturn)
    if df.is_empty() or log_ret not in df.columns: return 0.0
    series = df[log_ret].cast(pl.Float64)
    if downside: dev_log = math.sqrt(((series.clip(upper_bound=0.0)) ** 2).mean() or 0.0)
    elif upside: dev_log = math.sqrt(((series.clip(lower_bound=0.0)) ** 2).mean() or 0.0)
    else: dev_log = series.std() or 0.0
    return math.sqrt(math.exp(dev_log ** 2) - 1.0) * 100.0 if dev_log else 0.0

def calculate_annualized_volatility(vol: float, nr_trades: int, duration_seconds: float, trading_days: int = 365, pct: bool = False) -> float:
    if not vol or not nr_trades or not duration_seconds or duration_seconds <= 0.0: return 0.0
    vol = vol / 100.0 if pct else vol
    value = vol * math.sqrt(nr_trades * (trading_days * 86400.0) / duration_seconds)
    return calculate_percentage(value) if pct else value

def calculate_risk_to_reward(avg_win: float, avg_loss: float) -> float:
    return abs(avg_loss) / avg_win if avg_win else 0.0

def calculate_profit_factor(win_pnl: float, loss_pnl: float) -> float:
    return win_pnl / abs(loss_pnl) if loss_pnl else 0.0

def calculate_excursion(initial_balance: float, df: pl.DataFrame, drawdown: bool) -> tuple[float, float, float, float]:
    net_pnl = str(PositionAPI.ID.NetPnL)
    if df.is_empty() or net_pnl not in df.columns: return 0.0, 0.0, 0.0, 0.0
    cum_bal = df[net_pnl].cum_sum() + initial_balance
    if drawdown:
        reference = cum_bal.cum_max().clip(lower_bound=initial_balance)
        excursion = reference - cum_bal
    else:
        reference = cum_bal.cum_min().clip(upper_bound=initial_balance)
        excursion = cum_bal - reference
    excursion_pct = excursion / reference
    return excursion.max(), (excursion_pct.max() or 0.0) * 100.0, excursion.mean(), (excursion_pct.mean() or 0.0) * 100.0

def calculate_drawdown(initial_balance: float, df: pl.DataFrame) -> tuple[float, float, float, float]:
    return calculate_excursion(initial_balance, df, drawdown=True)

def calculate_runup(initial_balance: float, df: pl.DataFrame) -> tuple[float, float, float, float]:
    return calculate_excursion(initial_balance, df, drawdown=False)

def calculate_holding_times(df: pl.DataFrame, stop: date) -> tuple[float, float, float]:
    entry_ts = str(PositionAPI.ID.EntryTimestamp)
    exit_ts = str(TradeAPI.ID.ExitTimestamp)
    if df.is_empty() or entry_ts not in df.columns: return 0.0, 0.0, 0.0
    if exit_ts in df.columns:
        h_times = df[exit_ts] - df[entry_ts]
    else:
        stop_dt = datetime.combine(stop, datetime.min.time()) if isinstance(stop, date) and not isinstance(stop, datetime) else stop
        h_times = pl.Series([stop_dt] * len(df)) - df[entry_ts]
    def _days_(td: timedelta) -> float: return td.total_seconds() / 86400.0 if td else 0.0
    return _days_(h_times.max()), _days_(h_times.mean()), _days_(h_times.min())

def calculate_ratio(ann_ret_pct: float, risk_pct: float, rfr: float = 0.0) -> float:
    risk_pct = abs(risk_pct) if risk_pct else 1e-2
    return (ann_ret_pct - rfr) / risk_pct

def calculate_sharpe(ann_ret_pct: float, ann_vol_pct: float, rfr: float = 0.0) -> float:
    return calculate_ratio(ann_ret_pct, ann_vol_pct, rfr)

def calculate_sortino(ann_ret_pct: float, down_vol_pct: float, rfr: float = 0.0) -> float:
    return calculate_ratio(ann_ret_pct, down_vol_pct, rfr)

def calculate_calmar(ann_ret_pct: float, max_dd_pct: float, rfr: float = 0.0) -> float:
    return calculate_ratio(ann_ret_pct, max_dd_pct, rfr)

def calculate_sterling(ann_ret_pct: float, mean_dd_pct: float, rfr: float = 0.0) -> float:
    return calculate_ratio(ann_ret_pct, mean_dd_pct, rfr)

def equity_curve_ratios(curve: Union[list, None], start: date, stop: date, trading_days: int = 365, max_drawdown: Union[float, None] = None, mean_drawdown: Union[float, None] = None) -> Union[dict, None]:
    if not curve or len(curve) < 2: return None
    returns = [(curve[i] / curve[i - 1] - 1.0) if curve[i - 1] else 0.0 for i in range(1, len(curve))]
    n = len(returns)
    duration_seconds = calculate_duration_seconds(start, stop)
    years = duration_seconds / (trading_days * 86400.0) if duration_seconds and duration_seconds > 0.0 else 0.0
    periods = n / years if years > 0.0 else 0.0
    annualize = math.sqrt(periods) if periods > 0.0 else 0.0
    mean = sum(returns) / n
    variance = sum((value - mean) ** 2 for value in returns) / (n - 1) if n > 1 else 0.0
    deviation = math.sqrt(variance)
    downside = math.sqrt(sum(value ** 2 for value in returns if value < 0.0) / n)
    sharpe = (mean / deviation) * annualize if deviation > 0.0 else 0.0
    sortino = (mean / downside) * annualize if downside > 0.0 else 0.0
    if max_drawdown is None or mean_drawdown is None:
        peak, curve_max, curve_sum = curve[0], 0.0, 0.0
        for value in curve:
            if value > peak: peak = value
            drawdown = (peak - value) / peak if peak else 0.0
            if drawdown > curve_max: curve_max = drawdown
            curve_sum += drawdown
        max_drawdown = curve_max if max_drawdown is None else max_drawdown
        mean_drawdown = curve_sum / len(curve) if mean_drawdown is None else mean_drawdown
    total_return = (curve[-1] / curve[0] - 1.0) if curve[0] else 0.0
    annualized_return = ((1.0 + total_return) ** (1.0 / years) - 1.0) if years > 0.0 and (1.0 + total_return) > 0.0 else 0.0
    calmar = annualized_return / max_drawdown if max_drawdown > 0.0 else 0.0
    sterling = annualized_return / mean_drawdown if mean_drawdown > 0.0 else 0.0
    return {SHARPERATIO: sharpe, SORTINORATIO: sortino, CALMARRATIO: calmar, STERLINGRATIO: sterling}

def independent_metrics(initial_balance: float, start: date, stop: date, df: pl.DataFrame) -> dict:
    points = str(PositionAPI.ID.Points)
    pips = str(PositionAPI.ID.Pips)
    net_pnl = str(PositionAPI.ID.NetPnL)
    gross_pnl_col = str(PositionAPI.ID.GrossPnL)
    commission_pnl_col = str(PositionAPI.ID.CommissionPnL)
    swap_pnl_col = str(PositionAPI.ID.SwapPnL)

    win_df, loss_df = split_winning_losing(df)
    total_n = calculate_total(df)
    total_points = calculate_sum(df, points)
    total_pips = calculate_sum(df, pips)

    win_n = calculate_total(win_df)
    win_points = calculate_sum(win_df, points)
    win_pips = calculate_sum(win_df, pips)

    loss_n = calculate_total(loss_df)
    loss_points = calculate_sum(loss_df, points)
    loss_pips = calculate_sum(loss_df, pips)

    win_rate_pct = calculate_rate_perc(win_n, total_n)
    loss_rate_pct = calculate_rate_perc(loss_n, total_n)

    win_max_trade, win_avg_trade, win_min_trade = calculate_min_avg_max(win_n, win_df, net_pnl)
    loss_min_trade, loss_avg_trade, loss_max_trade = calculate_min_avg_max(loss_n, loss_df, net_pnl)
    win_max_pts, win_avg_pts, win_min_pts = calculate_min_avg_max(win_n, win_df, points)
    loss_min_pts, loss_avg_pts, loss_max_pts = calculate_min_avg_max(loss_n, loss_df, points)
    win_max_pips, win_avg_pips, win_min_pips = calculate_min_avg_max(win_n, win_df, pips)
    loss_min_pips, loss_avg_pips, loss_max_pips = calculate_min_avg_max(loss_n, loss_df, pips)

    gross_pnl = calculate_sum(df, gross_pnl_col)
    comm_pnl = calculate_sum(df, commission_pnl_col)
    swap_pnl = calculate_sum(df, swap_pnl_col)
    win_pnl = calculate_sum(win_df, net_pnl)
    loss_pnl = calculate_sum(loss_df, net_pnl)
    total_pnl = calculate_sum(df, net_pnl)

    exp_win_ret_pct, win_ret_pct = calculate_return(win_df)
    win_vol_pct = calculate_volatility(win_df)
    exp_loss_ret_pct, loss_ret_pct = calculate_return(loss_df)
    loss_vol_pct = calculate_volatility(loss_df)
    exp_net_ret_pct, net_ret_pct = calculate_return(df)
    net_vol_pct = calculate_volatility(df)

    up_vol_pct = calculate_volatility(df, upside=True)
    down_vol_pct = calculate_volatility(df, downside=True)

    duration_seconds = calculate_duration_seconds(start, stop)

    win_ret_annualized_pct = calculate_annualized_return(win_ret_pct, duration_seconds, pct=True)
    win_vol_annualized_pct = calculate_annualized_volatility(win_vol_pct, win_n, duration_seconds, pct=True)
    loss_ret_annualized_pct = calculate_annualized_return(loss_ret_pct, duration_seconds, pct=True)
    loss_vol_annualized_pct = calculate_annualized_volatility(loss_vol_pct, loss_n, duration_seconds, pct=True)
    net_ret_annualized_pct = calculate_annualized_return(net_ret_pct, duration_seconds, pct=True)
    up_vol_annualized_pct = calculate_annualized_volatility(up_vol_pct, total_n, duration_seconds, pct=True)
    down_vol_annualized_pct = calculate_annualized_volatility(down_vol_pct, total_n, duration_seconds, pct=True)
    net_vol_annualized_pct = calculate_annualized_volatility(net_vol_pct, total_n, duration_seconds, pct=True)

    avg_trade = calculate_average(total_pnl, total_n)
    avg_points = calculate_average(total_points, total_n)
    avg_pips = calculate_average(total_pips, total_n)

    exp_trade = calculate_expected(win_rate_pct, win_avg_trade, loss_rate_pct, loss_avg_trade)
    exp_points = calculate_expected(win_rate_pct, win_avg_pts, loss_rate_pct, loss_avg_pts)
    exp_pips = calculate_expected(win_rate_pct, win_avg_pips, loss_rate_pct, loss_avg_pips)

    rr_ratio = calculate_risk_to_reward(win_avg_trade, loss_avg_trade)
    profit_factor = calculate_profit_factor(win_pnl, loss_pnl)

    max_dd_val, max_dd_pct, mean_dd_val, mean_dd_pct = calculate_drawdown(initial_balance, df)
    max_ru_val, max_ru_pct, mean_ru_val, mean_ru_pct = calculate_runup(initial_balance, df)

    max_hold, avg_hold, min_hold = calculate_holding_times(df, stop)

    sharpe = calculate_sharpe(net_ret_annualized_pct, net_vol_annualized_pct)
    sortino = calculate_sortino(net_ret_annualized_pct, down_vol_annualized_pct)
    calmar = calculate_calmar(net_ret_annualized_pct, max_dd_pct)
    sterling = calculate_sterling(net_ret_annualized_pct, mean_dd_pct)

    return {
        TOTALTRADESVALUE: total_n,
        TOTALPOINTSVALUE: total_points,
        TOTALPIPSVALUE: total_pips,

        WINNINGTRADESVALUE: win_n,
        WINNINGPOINTSVALUE: win_points,
        WINNINGPIPSVALUE: win_pips,
        WINNINGRATEPERC: win_rate_pct,
        MAXWINNINGTRADE: win_max_trade,
        AVERAGEWINNINGTRADE: win_avg_trade,
        MINWINNINGTRADE: win_min_trade,
        MAXWINNINGPOINTS: win_max_pts,
        AVERAGEWINNINGPOINTS: win_avg_pts,
        MINWINNINGPOINTS: win_min_pts,
        MAXWINNINGPIPS: win_max_pips,
        AVERAGEWINNINGPIPS: win_avg_pips,
        MINWINNINGPIPS: win_min_pips,
        EXPECTEDWINNINGRETURNPERC: exp_win_ret_pct,
        WINNINGRETURNPERC: win_ret_pct,
        WINNINGRETURNANNPERC: win_ret_annualized_pct,
        WINNINGVOLATILITYPERC: win_vol_pct,
        WINNINGVOLATILITYANNPERC: win_vol_annualized_pct,

        LOSINGTRADESVALUE: loss_n,
        LOSINGPOINTSVALUE: loss_points,
        LOSINGPIPSVALUE: loss_pips,
        LOSINGRATEPERC: loss_rate_pct,
        MAXLOSINGTRADE: loss_max_trade,
        AVERAGELOSINGTRADE: loss_avg_trade,
        MINLOSINGTRADE: loss_min_trade,
        MAXLOSINGPOINTS: loss_max_pts,
        AVERAGELOSINGPOINTS: loss_avg_pts,
        MINLOSINGPOINTS: loss_min_pts,
        MAXLOSINGPIPS: loss_max_pips,
        AVERAGELOSINGPIPS: loss_avg_pips,
        MINLOSINGPIPS: loss_min_pips,
        EXPECTEDLOSINGRETURNPERC: exp_loss_ret_pct,
        LOSINGRETURNPERC: loss_ret_pct,
        LOSINGRETURNANNPERC: loss_ret_annualized_pct,
        LOSINGVOLATILITYPERC: loss_vol_pct,
        LOSINGVOLATILITYANNPERC: loss_vol_annualized_pct,

        AVERAGETRADE: avg_trade,
        AVERAGEPOINTS: avg_points,
        AVERAGEPIPS: avg_pips,
        EXPECTEDTRADE: exp_trade,
        EXPECTEDPOINTS: exp_points,
        EXPECTEDPIPS: exp_pips,

        GROSSPNLVALUE: gross_pnl,
        COMMISSIONSPNLVALUE: comm_pnl,
        SWAPSPNLVALUE: swap_pnl,
        NETPNLVALUE: total_pnl,
        EXPECTEDNETRETURNPERC: exp_net_ret_pct,
        NETRETURNPERC: net_ret_pct,
        NETRETURNANNPERC: net_ret_annualized_pct,
        UPSIDEVOLATILITYPERC: up_vol_pct,
        UPSIDEVOLATILITYANNPERC: up_vol_annualized_pct,
        DOWNSIDEVOLATILITYPERC: down_vol_pct,
        DOWNSIDEVOLATILITYANNPERC: down_vol_annualized_pct,
        NETVOLATILITYPERC: net_vol_pct,
        NETVOLATILITYANNPERC: net_vol_annualized_pct,

        PROFITFACTOR: profit_factor,
        RISKTOREWARDRATIO: rr_ratio,
        MAXBALANCEDRAWDOWNVALUE: max_dd_val,
        MAXBALANCEDRAWDOWNPERC: max_dd_pct,
        MEANBALANCEDRAWDOWNVALUE: mean_dd_val,
        MEANBALANCEDRAWDOWNPERC: mean_dd_pct,
        MAXBALANCERUNUPVALUE: max_ru_val,
        MAXBALANCERUNUPPERC: max_ru_pct,
        MEANBALANCERUNUPVALUE: mean_ru_val,
        MEANBALANCERUNUPPERC: mean_ru_pct,
        MAXHOLDINGTIME: max_hold,
        AVERAGEHOLDINGTIME: avg_hold,
        MINHOLDINGTIME: min_hold,
        SHARPERATIO: sharpe,
        SORTINORATIO: sortino,
        CALMARRATIO: calmar,
        STERLINGRATIO: sterling
    }

def dependent_metrics(initial_balance: float, start: date, stop: date, df: pl.DataFrame, buy_col: str, sell_col: str, total_col: str, equity: Union[dict, None] = None, ratios: Union[dict, None] = None, override: Union[dict, None] = None) -> pl.DataFrame:
    net_pnl = str(PositionAPI.ID.NetPnL)
    buy_df, sell_df = split_buy_sell(df)
    buy_metrics = independent_metrics(initial_balance, start, stop, buy_df)
    sell_metrics = independent_metrics(initial_balance, start, stop, sell_df)
    total_metrics = independent_metrics(initial_balance, start, stop, df)

    cur_win_streak = cur_loss_streak = 0
    max_win_streak = max_loss_streak = 0
    max_win_idx = max_loss_idx = 0

    if not df.is_empty() and net_pnl in df.columns:
        for idx, row in enumerate(df.iter_rows(named=True)):
            if row.get(net_pnl, 0.0) > 0:
                cur_win_streak += 1
                cur_loss_streak = 0
            else:
                cur_loss_streak += 1
                cur_win_streak = 0

            if cur_win_streak > max_win_streak:
                max_win_idx = idx
                max_win_streak = cur_win_streak
            if cur_loss_streak > max_loss_streak:
                max_loss_idx = idx
                max_loss_streak = cur_loss_streak

        win_streak_df = df.slice(offset=max_win_idx - max_win_streak + 1, length=max_win_streak)
        buy_win_streak_df, sell_win_streak_df = split_buy_sell(win_streak_df)
        buy_metrics[MAXWINNINGSTREAK] = calculate_total(buy_win_streak_df)
        sell_metrics[MAXWINNINGSTREAK] = calculate_total(sell_win_streak_df)
        total_metrics[MAXWINNINGSTREAK] = calculate_total(win_streak_df)

        loss_streak_df = df.slice(offset=max_loss_idx - max_loss_streak + 1, length=max_loss_streak)
        buy_loss_streak_df, sell_loss_streak_df = split_buy_sell(loss_streak_df)
        buy_metrics[MAXLOSINGSTREAK] = calculate_total(buy_loss_streak_df)
        sell_metrics[MAXLOSINGSTREAK] = calculate_total(sell_loss_streak_df)
        total_metrics[MAXLOSINGSTREAK] = calculate_total(loss_streak_df)
    else:
        buy_metrics[MAXWINNINGSTREAK] = 0
        sell_metrics[MAXWINNINGSTREAK] = 0
        total_metrics[MAXWINNINGSTREAK] = 0
        buy_metrics[MAXLOSINGSTREAK] = 0
        sell_metrics[MAXLOSINGSTREAK] = 0
        total_metrics[MAXLOSINGSTREAK] = 0

    equity_defaults = {
        MAXEQUITYDRAWDOWNVALUE: 0.0,
        MAXEQUITYDRAWDOWNPERC: 0.0,
        MEANEQUITYDRAWDOWNVALUE: 0.0,
        MEANEQUITYDRAWDOWNPERC: 0.0,
        MAXEQUITYRUNUPVALUE: 0.0,
        MAXEQUITYRUNUPPERC: 0.0,
        MEANEQUITYRUNUPVALUE: 0.0,
        MEANEQUITYRUNUPPERC: 0.0
    }
    for metrics in (buy_metrics, sell_metrics, total_metrics):
        metrics.update(equity_defaults)
        if equity: metrics.update(equity)
    if ratios: total_metrics.update(ratios)
    if override: total_metrics.update(override)

    return pl.DataFrame({
        buy_col: [buy_metrics[k] for k in Metrics],
        sell_col: [sell_metrics[k] for k in Metrics],
        total_col: [total_metrics[k] for k in Metrics]
    }, strict=False)

def _safe_df_(df: pl.DataFrame) -> pl.DataFrame:
    if not df.is_empty(): return df
    float_cols = [
        str(PositionAPI.ID.UID), str(TradeAPI.ID.Position), str(PositionAPI.ID.EntryPrice), str(TradeAPI.ID.ExitPrice),
        str(PositionAPI.ID.Volume), str(PositionAPI.ID.Points), str(PositionAPI.ID.Pips),
        str(PositionAPI.ID.GrossPnL), str(PositionAPI.ID.CommissionPnL), str(PositionAPI.ID.SwapPnL), str(PositionAPI.ID.NetPnL),
        str(PositionAPI.ID.MaxEquityDrawdownPoints), str(PositionAPI.ID.MaxEquityDrawdownPips),
        str(PositionAPI.ID.MaxEquityRunupPoints), str(PositionAPI.ID.MaxEquityRunupPips),
        str(PositionAPI.ID.Return), str(PositionAPI.ID.LogReturn),
        str(PositionAPI.ID.MaxEquityDrawdownReturn), str(PositionAPI.ID.RiskAdjustedReturn),
        str(PositionAPI.ID.EntryBalance), str(PositionAPI.ID.MidBalance), str(TradeAPI.ID.ExitBalance),
    ]
    schema: dict[str, pl.DataType] = {col: pl.Float64() for col in float_cols}
    schema[str(PositionAPI.ID.EntryTimestamp)] = pl.Datetime()
    schema[str(TradeAPI.ID.ExitTimestamp)] = pl.Datetime()
    schema[str(PositionAPI.ID.Direction)] = pl.String()
    return pl.DataFrame(schema=schema)

def generate_realized_report(trades_df: pl.DataFrame, account: AccountAPI, start: date, stop: date) -> pl.DataFrame:
    initial_balance = (account.Balance if account is not None else 0.0) or 0.0
    safe_trades = _safe_df_(trades_df)
    ind = sort_items(safe_trades)
    ind_df = dependent_metrics(initial_balance, start, stop, ind, REALIZED_BUY_INDIVIDUAL, REALIZED_SELL_INDIVIDUAL, REALIZED_TOTAL_INDIVIDUAL)
    agg = sort_items(aggregate_items(safe_trades))
    agg_df = dependent_metrics(initial_balance, start, stop, agg, REALIZED_BUY_AGGREGATED, REALIZED_SELL_AGGREGATED, REALIZED_TOTAL_AGGREGATED)
    labels_df = pl.DataFrame({STATISTICS_METRICS_LABEL: Metrics})
    return pl.concat([labels_df, ind_df, agg_df], how="horizontal_extend")

def generate_unrealized_report(positions_df: pl.DataFrame, account: AccountAPI, start: date, stop: date) -> pl.DataFrame:
    initial_balance = (account.Balance if account is not None else 0.0) or 0.0
    safe_positions = _safe_df_(positions_df)
    ind = sort_items(safe_positions)
    ind_df = dependent_metrics(initial_balance, start, stop, ind, UNREALIZED_BUY_INDIVIDUAL, UNREALIZED_SELL_INDIVIDUAL, UNREALIZED_TOTAL_INDIVIDUAL)
    agg = sort_items(aggregate_items(safe_positions))
    agg_df = dependent_metrics(initial_balance, start, stop, agg, UNREALIZED_BUY_AGGREGATED, UNREALIZED_SELL_AGGREGATED, UNREALIZED_TOTAL_AGGREGATED)
    labels_df = pl.DataFrame({STATISTICS_METRICS_LABEL: Metrics})
    return pl.concat([labels_df, ind_df, agg_df], how="horizontal_extend")

def equity_metrics(initial_balance: float, deals: pl.DataFrame) -> dict:
    entry_bal, mid_bal = str(PositionAPI.ID.EntryBalance), str(PositionAPI.ID.MidBalance)
    ddr, rur = str(PositionAPI.ID.MaxEquityDrawdownReturn), str(PositionAPI.ID.MaxEquityRunupReturn)
    zero = {MAXEQUITYDRAWDOWNVALUE: 0.0, MAXEQUITYDRAWDOWNPERC: 0.0, MEANEQUITYDRAWDOWNVALUE: 0.0, MEANEQUITYDRAWDOWNPERC: 0.0, MAXEQUITYRUNUPVALUE: 0.0, MAXEQUITYRUNUPPERC: 0.0, MEANEQUITYRUNUPVALUE: 0.0, MEANEQUITYRUNUPPERC: 0.0}
    if deals.is_empty() or entry_bal not in deals.columns: return zero
    points = []
    for row in deals.iter_rows(named=True):
        opened = row.get(entry_bal) or initial_balance
        points.append(opened)
        points.append(opened + (row.get(rur) or 0.0) * opened)
        points.append(opened + (row.get(ddr) or 0.0) * opened)
        if row.get(mid_bal) is not None: points.append(row.get(mid_bal))
    peak = trough = points[0]
    max_dd = max_ru = drawdown_sum = runup_sum = 0.0
    for value in points:
        peak = max(peak, value)
        trough = min(trough, value)
        max_dd = max(max_dd, peak - value)
        max_ru = max(max_ru, value - trough)
        drawdown_sum += peak - value
        runup_sum += value - trough
    mean_dd, mean_ru = drawdown_sum / len(points), runup_sum / len(points)
    return {
        MAXEQUITYDRAWDOWNVALUE: max_dd,
        MAXEQUITYDRAWDOWNPERC: (max_dd / peak) * 100.0 if peak else 0.0,
        MEANEQUITYDRAWDOWNVALUE: mean_dd,
        MEANEQUITYDRAWDOWNPERC: (mean_dd / peak) * 100.0 if peak else 0.0,
        MAXEQUITYRUNUPVALUE: max_ru,
        MAXEQUITYRUNUPPERC: (max_ru / trough) * 100.0 if trough else 0.0,
        MEANEQUITYRUNUPVALUE: mean_ru,
        MEANEQUITYRUNUPPERC: (mean_ru / trough) * 100.0 if trough else 0.0
    }

def _equity_excursion_(excursions: dict) -> dict:
    return {
        MAXEQUITYDRAWDOWNVALUE: excursions["max_drawdown_value"],
        MAXEQUITYDRAWDOWNPERC: excursions["max_drawdown"] * 100.0,
        MEANEQUITYDRAWDOWNVALUE: excursions["mean_drawdown_value"],
        MEANEQUITYDRAWDOWNPERC: excursions["mean_drawdown"] * 100.0,
        MAXEQUITYRUNUPVALUE: excursions["max_runup_value"],
        MAXEQUITYRUNUPPERC: excursions["max_runup"] * 100.0,
        MEANEQUITYRUNUPVALUE: excursions["mean_runup_value"],
        MEANEQUITYRUNUPPERC: excursions["mean_runup"] * 100.0
    }

def generate_net_report(positions_df: pl.DataFrame, trades_df: pl.DataFrame, account: Union[AccountAPI, None], start: date, stop: date, equity_curve: Union[list, None] = None, excursions: Union[dict, None] = None) -> pl.DataFrame:
    initial_balance = (account.Balance if account is not None else 0.0) or 0.0
    safe_positions = _safe_df_(positions_df)
    safe_trades = _safe_df_(trades_df)
    if not safe_trades.is_empty() and not safe_positions.is_empty():
        common_cols = list(set(safe_trades.columns).intersection(safe_positions.columns))
        net_df = pl.concat([safe_trades.select(common_cols), safe_positions.select(common_cols)], how="vertical_relaxed")
    elif not safe_trades.is_empty():
        net_df = safe_trades
    else:
        net_df = safe_positions
    ind = sort_items(net_df)
    agg = sort_items(aggregate_items(net_df))
    equity = equity_metrics(initial_balance, agg)
    max_drawdown = excursions["max_drawdown"] if excursions else None
    mean_drawdown = excursions["mean_drawdown"] if excursions else None
    ratios = equity_curve_ratios(equity_curve, start, stop, max_drawdown=max_drawdown, mean_drawdown=mean_drawdown)
    override = _equity_excursion_(excursions) if excursions else None
    ind_df = dependent_metrics(initial_balance, start, stop, ind, NET_BUY_INDIVIDUAL, NET_SELL_INDIVIDUAL, NET_TOTAL_INDIVIDUAL, equity, ratios, override)
    agg_df = dependent_metrics(initial_balance, start, stop, agg, NET_BUY_AGGREGATED, NET_SELL_AGGREGATED, NET_TOTAL_AGGREGATED, equity, ratios, override)
    labels_df = pl.DataFrame({STATISTICS_METRICS_LABEL: Metrics})
    return pl.concat([labels_df, ind_df, agg_df], how="horizontal_extend")