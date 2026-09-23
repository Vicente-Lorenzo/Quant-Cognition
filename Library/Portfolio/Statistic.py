from __future__ import annotations

import math
from datetime import date
from typing import Union, TYPE_CHECKING

from Library.Database.Dataframe import pl
from Library.Market.Price import Direction
from Library.Portfolio.Order import OrderAPI
from Library.Portfolio.Position import PositionAPI
from Library.Portfolio.Trade import TradeAPI
from Library.Statistic.Curve import CurveAPI
from Library.Statistic.Label import *
from Library.Statistic.Metric import (
    align_series,
    calculate_annualized_return,
    calculate_annualized_volatility,
    calculate_average,
    calculate_duration_seconds,
    calculate_expected,
    calculate_profit_factor,
    calculate_rate_perc,
    calculate_risk_to_reward,
    calculate_years,
    daily_series,
    relative_metrics,
    standalone_metrics
)
from Library.Utility.Datetime import parse_datetime
from Library.Utility.Typing import MISSING

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
    RISKFREERATEPERC,
    SHARPERATIO,
    SHARPERATIOANN,
    SORTINORATIO,
    SORTINORATIOANN,
    CALMARRATIO,
    CALMARRATIOANN,
    STERLINGRATIO,
    STERLINGRATIOANN
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
    str(TradeAPI.ID.UID): pl.List(pl.Int64),
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

if TYPE_CHECKING:
    from Library.Portfolio.Account import AccountAPI

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

def realize_items(df: pl.DataFrame) -> pl.DataFrame:
    exit_ts = str(TradeAPI.ID.ExitTimestamp)
    entry_ts = str(PositionAPI.ID.EntryTimestamp)
    if df.is_empty() or exit_ts not in df.columns or entry_ts not in df.columns: return sort_items(df)
    return df.sort(by=[exit_ts, entry_ts], nulls_last=True, maintain_order=True)

def aggregate_items(df: pl.DataFrame) -> pl.DataFrame:
    position = str(TradeAPI.ID.Position)
    if df.is_empty() or position not in df.columns: return df
    volume = str(PositionAPI.ID.Volume)
    def _take_(col: str, op):
        return op(pl.col(col)) if col in df.columns else pl.lit(0.0).alias(col)
    def _weighted_(col: str):
        return ((pl.col(col) * pl.col(volume)).sum() / pl.col(volume).sum()).alias(col) if col in df.columns else pl.lit(0.0).alias(col)
    direction = str(PositionAPI.ID.Direction)
    bought = pl.col(volume).filter(pl.col(direction) == Direction.Buy.name).sum()
    sold = pl.col(volume).filter(pl.col(direction) == Direction.Sell.name).sum()
    agg_exprs = [
        pl.col(str(PositionAPI.ID.UID)),
        pl.when(bought >= sold).then(pl.lit(Direction.Buy.name)).otherwise(pl.lit(Direction.Sell.name)).alias(direction),
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
            pl.when(pl.col(exit_ts).null_count() > 0).then(None).otherwise(pl.col(exit_ts).max()).alias(exit_ts),
            pl.col(str(TradeAPI.ID.ExitPrice)).last(),
            _take_(str(TradeAPI.ID.ExitBalance), lambda x: x.last()),
        ])
    return df.group_by(position, maintain_order=True).agg(agg_exprs)

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

def calculate_min_avg_max(nr_items: int, df: pl.DataFrame, column: str) -> tuple[float, float, float]:
    if nr_items > 0 and column in df.columns:
        return df[column].max(), df[column].mean(), df[column].min()
    return 0.0, 0.0, 0.0

def calculate_sum(df: pl.DataFrame, column: str) -> float:
    return df[column].sum() if not df.is_empty() and column in df.columns else 0.0

def calculate_return(initial_balance: float, df: pl.DataFrame) -> tuple[float, float]:
    net_pnl = str(PositionAPI.ID.NetPnL)
    if not initial_balance or df.is_empty() or net_pnl not in df.columns: return 0.0, 0.0
    tot_ret_pct = calculate_sum(df, net_pnl) / initial_balance * 100.0
    return calculate_average(tot_ret_pct, calculate_total(df)), tot_ret_pct

def calculate_volatility(df: pl.DataFrame) -> float:
    log_ret = str(PositionAPI.ID.LogReturn)
    if df.is_empty() or log_ret not in df.columns: return 0.0
    dev_log = df[log_ret].cast(pl.Float64).std() or 0.0
    return math.sqrt(math.exp(dev_log ** 2) - 1.0) * 100.0 if dev_log else 0.0

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
    stop_dt = parse_datetime(stop)
    exits = df[exit_ts].fill_null(stop_dt) if exit_ts in df.columns else pl.Series([stop_dt] * len(df))
    seconds = (exits - df[entry_ts]).dt.total_seconds().clip(lower_bound=0)
    def _days_(value) -> float: return float(value) / 86400.0 if value is not None else 0.0
    return _days_(seconds.max()), _days_(seconds.mean()), _days_(seconds.min())

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

    exp_win_ret_pct, win_ret_pct = calculate_return(initial_balance, win_df)
    win_vol_pct = calculate_volatility(win_df)
    exp_loss_ret_pct, loss_ret_pct = calculate_return(initial_balance, loss_df)
    loss_vol_pct = calculate_volatility(loss_df)
    exp_net_ret_pct, net_ret_pct = calculate_return(initial_balance, df)

    duration_seconds = calculate_duration_seconds(start, stop)
    years = calculate_years(start, stop)

    win_ret_annualized_pct = win_ret_pct / years if years else 0.0
    win_vol_annualized_pct = calculate_annualized_volatility(win_vol_pct, win_n, duration_seconds, pct=True)
    loss_ret_annualized_pct = loss_ret_pct / years if years else 0.0
    loss_vol_annualized_pct = calculate_annualized_volatility(loss_vol_pct, loss_n, duration_seconds, pct=True)
    net_ret_annualized_pct = calculate_annualized_return(net_ret_pct, duration_seconds, pct=True)

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
        MINHOLDINGTIME: min_hold
    }

def dependent_metrics(initial_balance: float, start: date, stop: date, df: pl.DataFrame, buy_col: str, sell_col: str, total_col: str, curves: tuple = MISSING) -> pl.DataFrame:
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

    buy_curve, sell_curve, total_curve = curves if curves else (CurveAPI(), CurveAPI(), CurveAPI())
    buy_metrics.update(buy_curve.metrics(start, stop))
    sell_metrics.update(sell_curve.metrics(start, stop))
    total_metrics.update(total_curve.metrics(start, stop))

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

def _balance_(account: Union[AccountAPI, None], curves: tuple = MISSING) -> float:
    return (curves[2].Origin if curves else None) or (account.Balance if account is not None else 0.0) or 0.0

def _report_(initial_balance: float, start: date, stop: date, individual: pl.DataFrame, aggregated: pl.DataFrame, columns: tuple, curves: tuple = MISSING) -> pl.DataFrame:
    ind_df = dependent_metrics(initial_balance, start, stop, individual, *columns[:3], curves)
    agg_df = dependent_metrics(initial_balance, start, stop, aggregated, *columns[3:], curves)
    labels_df = pl.DataFrame({STATISTICS_METRICS_LABEL: Metrics})
    return pl.concat([labels_df, ind_df, agg_df], how="horizontal_extend")

def generate_realized_report(trades_df: pl.DataFrame, account: AccountAPI, start: date, stop: date) -> pl.DataFrame:
    safe_trades = _safe_df_(trades_df)
    columns = (REALIZED_BUY_INDIVIDUAL, REALIZED_SELL_INDIVIDUAL, REALIZED_TOTAL_INDIVIDUAL, REALIZED_BUY_AGGREGATED, REALIZED_SELL_AGGREGATED, REALIZED_TOTAL_AGGREGATED)
    return _report_(_balance_(account), start, stop, realize_items(safe_trades), realize_items(aggregate_items(safe_trades)), columns)

def generate_unrealized_report(positions_df: pl.DataFrame, account: AccountAPI, start: date, stop: date) -> pl.DataFrame:
    safe_positions = _safe_df_(positions_df)
    columns = (UNREALIZED_BUY_INDIVIDUAL, UNREALIZED_SELL_INDIVIDUAL, UNREALIZED_TOTAL_INDIVIDUAL, UNREALIZED_BUY_AGGREGATED, UNREALIZED_SELL_AGGREGATED, UNREALIZED_TOTAL_AGGREGATED)
    return _report_(_balance_(account), start, stop, realize_items(safe_positions), realize_items(aggregate_items(safe_positions)), columns)

def _aligned_positions_(positions: pl.DataFrame, trades: pl.DataFrame) -> pl.DataFrame:
    uid = str(PositionAPI.ID.UID)
    position = str(TradeAPI.ID.Position)
    exit_timestamp = str(TradeAPI.ID.ExitTimestamp)
    if position in trades.columns and position not in positions.columns and uid in positions.columns:
        positions = positions.with_columns(pl.col(uid).cast(trades.schema[position]).alias(position))
    if exit_timestamp in trades.columns and exit_timestamp not in positions.columns:
        positions = positions.with_columns(pl.lit(None).cast(trades.schema[exit_timestamp]).alias(exit_timestamp))
    return positions

def generate_net_report(positions_df: pl.DataFrame, trades_df: pl.DataFrame, account: Union[AccountAPI, None], start: date, stop: date, curves: tuple = MISSING) -> pl.DataFrame:
    initial_balance = _balance_(account, curves)
    safe_positions = _safe_df_(positions_df)
    safe_trades = _safe_df_(trades_df)
    if not safe_trades.is_empty() and not safe_positions.is_empty():
        safe_positions = _aligned_positions_(safe_positions, safe_trades)
        common_cols = [column for column in safe_trades.columns if column in safe_positions.columns]
        net_df = pl.concat([safe_trades.select(common_cols), safe_positions.select(common_cols)], how="vertical_relaxed")
    elif not safe_trades.is_empty():
        net_df = safe_trades
    else:
        net_df = safe_positions
    columns = (NET_BUY_INDIVIDUAL, NET_SELL_INDIVIDUAL, NET_TOTAL_INDIVIDUAL, NET_BUY_AGGREGATED, NET_SELL_AGGREGATED, NET_TOTAL_AGGREGATED)
    return _report_(initial_balance, start, stop, realize_items(net_df), realize_items(aggregate_items(net_df)), columns, curves)

def generate_benchmark_report(equity: Union[list, None], benchmarks: Union[dict, None], start: date, stop: date, trading_days: int = 365, risk_free: float = 0.0) -> pl.DataFrame:
    if not equity or len(equity) < 2: return pl.DataFrame()
    spine = [stamp for stamp, _ in equity]
    values = [value for _, value in equity]
    sampled = daily_series(spine, values)
    strategy = standalone_metrics(values, start, stop, trading_days, risk_free)
    if not strategy: return pl.DataFrame()
    columns = [BENCHMARK_TOTALRETURN, BENCHMARK_ANNUALIZEDRETURN, BENCHMARK_VOLATILITY, BENCHMARK_MAXDRAWDOWN,
               SHARPERATIOANN, SORTINORATIOANN, CALMARRATIOANN, STERLINGRATIOANN,
               BENCHMARK_CORRELATION, BENCHMARK_ALPHA, BENCHMARK_ALPHASIGNIFICANCE, BENCHMARK_BETA,
               BENCHMARK_TRACKINGERROR, BENCHMARK_INFORMATIONRATIO,
               BENCHMARK_EXCESSRETURN, BENCHMARK_UPSIDECAPTURE, BENCHMARK_DOWNSIDECAPTURE]
    rows = [{BENCHMARK_LABEL: "Strategy", **{column: strategy.get(column) for column in columns}}]
    for label, series in (benchmarks or {}).items():
        aligned = align_series(spine, series)
        metrics = standalone_metrics(aligned, start, stop, trading_days, risk_free)
        if not metrics:
            rows.append({BENCHMARK_LABEL: label, **{column: None for column in columns}})
            continue
        reference = daily_series(spine, aligned)
        cadence = len(sampled) / (calculate_duration_seconds(start, stop) / (trading_days * 86400.0)) if calculate_duration_seconds(start, stop) else 0.0
        relative = relative_metrics(
            sampled,
            reference,
            cadence or strategy["_periods_"],
            risk_free,
            annual=strategy.get(BENCHMARK_ANNUALIZEDRETURN, 0.0) / 100.0,
            reference=metrics.get(BENCHMARK_ANNUALIZEDRETURN, 0.0) / 100.0
        )
        relative[BENCHMARK_EXCESSRETURN] = (strategy["_total_"] - metrics["_total_"]) * 100.0
        rows.append({BENCHMARK_LABEL: label, **{column: metrics.get(column, relative.get(column)) for column in columns}})
    return pl.DataFrame(rows)