from __future__ import annotations

import math
from datetime import date, timedelta, datetime
from typing import Union, TYPE_CHECKING

from Library.Database.Dataframe import pl
from Library.Market.Price import Direction

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

def calculate_annualized_return(ret: float, duration_seconds: float, trading_days: int = 365) -> float:
    if not ret or not duration_seconds or duration_seconds <= 0.0: return 0.0
    return ((1.0 + ret) ** ((trading_days * 86400.0) / duration_seconds)) - 1.0

def calculate_annualized_log_return(log_ret: float, duration_seconds: float, trading_days: int = 365) -> float:
    if log_ret is None or not duration_seconds or duration_seconds <= 0.0: return 0.0
    return log_ret * ((trading_days * 86400.0) / duration_seconds)

def calculate_pnl_difference(current_price: float, entry_price: float, is_long: bool) -> float:
    return (current_price - entry_price) if is_long else (entry_price - current_price)

def calculate_gross_pnl(pnl_diff: float, volume: float) -> float:
    return pnl_diff * volume

def calculate_net_pnl(gross_pnl: float, commission_pnl: float, swap_pnl: float) -> float:
    return gross_pnl + commission_pnl + swap_pnl


# Report Constants
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
WINNINGRETURNANNPERC = "Winning Return Annualised (%) [µ_up]"
WINNINGVOLATILITYPERC = "Winning Volatility (%)"
WINNINGVOLATILITYANNPERC = "Winning Volatility Annualised (%) [σ_up]"

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
LOSINGRETURNANNPERC = "Losing Return Annualised (%) [µ_down]"
LOSINGVOLATILITYPERC = "Losing Volatility (%)"
LOSINGVOLATILITYANNPERC = "Losing Volatility Annualised (%) [σ_down]"

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
NETRETURNANNPERC = "Net Return Annualised (%) [µ]"
NETVOLATILITYPERC = "Net Volatility (%)"
NETVOLATILITYANNPERC = "Net Volatility Annualised (%) [σ]"

PROFITFACTOR = "Profit Factor"
RISKTOREWARDRATIO = "Risk-to-Reward Ratio"
MAXDRAWDOWNVALUE = "Max Drawdown"
MAXDRAWDOWNPERC = "Max Drawdown (%)"
MEANDRAWDOWNVALUE = "Mean Drawdown"
MEANDRAWDOWNPERC = "Mean Drawdown (%)"
MAXRUNUPVALUE = "Max Runup"
MAXRUNUPPERC = "Max Runup (%)"
MEANRUNUPVALUE = "Mean Runup"
MEANRUNUPPERC = "Mean Runup (%)"
MAXHOLDINGTIME = "Max Holding Time (Days)"
AVERAGEHOLDINGTIME = "Avg Holding Time (Days)"
MINHOLDINGTIME = "Min Holding Time (Days)"
SHARPERATIO = "Sharpe Ratio"
SORTINORATIO = "Sortino Ratio"
CALMARRATIO = "Calmar Ratio"
FITNESSRATIO = "Fitness Ratio"

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
    NETVOLATILITYPERC,
    NETVOLATILITYANNPERC,

    PROFITFACTOR,
    RISKTOREWARDRATIO,
    MAXDRAWDOWNVALUE,
    MAXDRAWDOWNPERC,
    MEANDRAWDOWNVALUE,
    MEANDRAWDOWNPERC,
    MAXRUNUPVALUE,
    MAXRUNUPPERC,
    MEANRUNUPVALUE,
    MEANRUNUPPERC,
    MAXHOLDINGTIME,
    AVERAGEHOLDINGTIME,
    MINHOLDINGTIME,
    SHARPERATIO,
    SORTINORATIO,
    CALMARRATIO,
    FITNESSRATIO
]

def sort_items(df: pl.DataFrame) -> pl.DataFrame:
    from Library.Portfolio.Position import PositionAPI
    entry_ts = str(PositionAPI.ID.EntryTimestamp)
    if df.is_empty() or entry_ts not in df.columns: return df
    return df.sort(by=entry_ts, descending=False)

def aggregate_items(df: pl.DataFrame) -> pl.DataFrame:
    from Library.Portfolio.Position import PositionAPI
    from Library.Portfolio.Trade import TradeAPI
    if df.is_empty() or "Position" not in df.columns: return df
    
    uid_col = str(PositionAPI.ID.UID)
    dir_col = str(PositionAPI.ID.Direction)
    entry_ts = str(PositionAPI.ID.EntryTimestamp)
    entry_price = str(PositionAPI.ID.EntryPrice)
    vol_col = str(PositionAPI.ID.Volume)
    gross_pnl = str(PositionAPI.ID.GrossPnL)
    comm_pnl = str(PositionAPI.ID.CommissionPnL)
    swap_pnl = str(PositionAPI.ID.SwapPnL)
    net_pnl = str(PositionAPI.ID.NetPnL)
    entry_bal = str(PositionAPI.ID.EntryBalance)

    exit_ts = str(TradeAPI.ID.ExitTimestamp)
    exit_price = str(TradeAPI.ID.ExitPrice)
    exit_bal = str(TradeAPI.ID.ExitBalance)

    agg_exprs = [
        pl.col(uid_col).first(),
        pl.col(dir_col).first(),
        pl.col(entry_ts).min(),
        pl.col(entry_price).first(),
        pl.col(vol_col).sum(),
        pl.col("Points").sum() if "Points" in df.columns else pl.lit(0.0).alias("Points"),
        pl.col("Pips").sum() if "Pips" in df.columns else pl.lit(0.0).alias("Pips"),
        pl.col(gross_pnl).sum() if gross_pnl in df.columns else pl.lit(0.0).alias(gross_pnl),
        pl.col(comm_pnl).sum() if comm_pnl in df.columns else pl.lit(0.0).alias(comm_pnl),
        pl.col(swap_pnl).sum() if swap_pnl in df.columns else pl.lit(0.0).alias(swap_pnl),
        pl.col(net_pnl).sum() if net_pnl in df.columns else pl.lit(0.0).alias(net_pnl),
        pl.col("DrawdownPoints").min() if "DrawdownPoints" in df.columns else pl.lit(0.0).alias("DrawdownPoints"),
        pl.col("DrawdownPips").min() if "DrawdownPips" in df.columns else pl.lit(0.0).alias("DrawdownPips"),
        pl.col("RunupPoints").max() if "RunupPoints" in df.columns else pl.lit(0.0).alias("RunupPoints"),
        pl.col("RunupPips").max() if "RunupPips" in df.columns else pl.lit(0.0).alias("RunupPips"),
        pl.col("NetReturn").sum() if "NetReturn" in df.columns else pl.lit(0.0).alias("NetReturn"),
        pl.col("NetLogReturn").sum() if "NetLogReturn" in df.columns else pl.lit(0.0).alias("NetLogReturn"),
        pl.col("DrawdownReturn").min() if "DrawdownReturn" in df.columns else pl.lit(0.0).alias("DrawdownReturn"),
        pl.col("NetReturnDrawdown").sum() if "NetReturnDrawdown" in df.columns else pl.lit(0.0).alias("NetReturnDrawdown"),
        pl.col(entry_bal).first() if entry_bal in df.columns else pl.lit(0.0).alias(entry_bal),
    ]

    if exit_ts in df.columns:
        agg_exprs.extend([
            pl.col(exit_ts).max(),
            pl.col(exit_price).last(),
            pl.col(exit_bal).last() if exit_bal in df.columns else pl.lit(0.0).alias(exit_bal)
        ])
        
    return df.group_by("Position").agg(agg_exprs)

def split_buy_sell(df: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame]:
    from Library.Portfolio.Position import PositionAPI
    dir_col = str(PositionAPI.ID.Direction)
    if df.is_empty() or dir_col not in df.columns: return df, df
    return (df.filter(pl.col(dir_col) == Direction.Buy.name),
            df.filter(pl.col(dir_col) == Direction.Sell.name))

def split_winning_losing(df: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame]:
    from Library.Portfolio.Position import PositionAPI
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

def calculate_return_and_volatility(df: pl.DataFrame) -> tuple[float, float, float]:
    if df.is_empty() or "NetLogReturn" not in df.columns: return 0.0, 0.0, 0.0
    exp_log = df["NetLogReturn"].mean()
    tot_log = df["NetLogReturn"].sum()
    vol_log = df["NetLogReturn"].std()
    exp_ret = (math.exp(exp_log) - 1.0) * 100.0 if exp_log else 0.0
    tot_ret = (math.exp(tot_log) - 1.0) * 100.0 if tot_log else 0.0
    vol_ret = math.sqrt(math.exp((vol_log or 0.0)**2) - 1.0) * 100.0 if vol_log else 0.0
    return exp_ret, tot_ret, vol_ret

def calculate_ann_return(start: date, stop: date, ret_perc: float, days: int = 365) -> float:
    if not ret_perc or not start or not stop: return 0.0
    delta = (stop - start).days
    if delta <= 0: return 0.0
    return (((1.0 + (ret_perc / 100.0)) ** (days / delta)) - 1.0) * 100.0

def calculate_ann_volatility(start: date, stop: date, vol_perc: float, days: int = 365) -> float:
    if not vol_perc or not start or not stop: return 0.0
    delta = (stop - start).days
    if delta <= 0: return 0.0
    return (vol_perc / 100.0) * math.sqrt(days / delta) * 100.0

def calculate_risk_to_reward(avg_win: float, avg_loss: float) -> float:
    return abs(avg_loss) / avg_win if avg_win else 0.0

def calculate_profit_factor(win_pnl: float, loss_pnl: float) -> float:
    return win_pnl / abs(loss_pnl) if loss_pnl else 0.0

def calculate_drawdown(initial_balance: float, df: pl.DataFrame) -> tuple[float, float, float, float]:
    from Library.Portfolio.Position import PositionAPI
    net_pnl = str(PositionAPI.ID.NetPnL)
    if df.is_empty() or net_pnl not in df.columns: return 0.0, 0.0, 0.0, 0.0
    cum_bal = df[net_pnl].cum_sum() + initial_balance
    run_max = cum_bal.cum_max()
    dd = run_max - cum_bal
    max_dd_val = dd.max()
    cum_max_val = run_max.max()
    max_dd_pct = (max_dd_val / cum_max_val) * 100.0 if cum_max_val else 0.0
    mean_dd_val = dd.mean()
    mean_dd_pct = (mean_dd_val / cum_max_val) * 100.0 if cum_max_val else 0.0
    return max_dd_val, max_dd_pct, mean_dd_val, mean_dd_pct

def calculate_runup(initial_balance: float, df: pl.DataFrame) -> tuple[float, float, float, float]:
    from Library.Portfolio.Position import PositionAPI
    net_pnl = str(PositionAPI.ID.NetPnL)
    if df.is_empty() or net_pnl not in df.columns: return 0.0, 0.0, 0.0, 0.0
    cum_bal = df[net_pnl].cum_sum() + initial_balance
    run_min = cum_bal.cum_min()
    ru = cum_bal - run_min
    max_ru_val = ru.max()
    cum_min_val = run_min.min()
    max_ru_pct = (max_ru_val / cum_min_val) * 100.0 if cum_min_val else 0.0
    mean_ru_val = ru.mean()
    mean_ru_pct = (mean_ru_val / cum_min_val) * 100.0 if cum_min_val else 0.0
    return max_ru_val, max_ru_pct, mean_ru_val, mean_ru_pct

def calculate_holding_times(df: pl.DataFrame, stop: date) -> tuple[float, float, float]:
    from Library.Portfolio.Position import PositionAPI
    from Library.Portfolio.Trade import TradeAPI
    entry_ts = str(PositionAPI.ID.EntryTimestamp)
    exit_ts = str(TradeAPI.ID.ExitTimestamp)
    if df.is_empty() or entry_ts not in df.columns: return 0.0, 0.0, 0.0
    if exit_ts in df.columns:
        h_times = df[exit_ts] - df[entry_ts]
    else:
        if isinstance(stop, date) and not isinstance(stop, datetime):
            stop_dt = datetime.combine(stop, datetime.min.time())
        else:
            stop_dt = stop
        h_times = pl.Series([stop_dt] * len(df)) - df[entry_ts]
    
    def fmt(td: timedelta): return td.days + (td.seconds // 3600) / 100.0 if td else 0.0
    return fmt(h_times.max()), fmt(h_times.mean()), fmt(h_times.min())

def calculate_sharpe(ann_ret: float, ann_vol: float, rfr: float = 0.0) -> float:
    ann_vol = ann_vol if ann_vol else 1e-2
    return (ann_ret - rfr) / ann_vol

def calculate_sortino(ann_ret: float, down_vol: float, rfr: float = 0.0) -> float:
    down_vol = down_vol if down_vol else 1e-2
    return (ann_ret - rfr) / down_vol

def calculate_calmar(ann_ret: float, max_dd_pct: float, rfr: float = 0.0) -> float:
    max_dd_pct = max_dd_pct if max_dd_pct else 1e-2
    return (ann_ret - rfr) / abs(max_dd_pct)

def calculate_fitness(ann_ret: float, mean_dd_pct: float, rfr: float = 0.0) -> float:
    mean_dd_pct = mean_dd_pct if mean_dd_pct else 1e-2
    return (ann_ret - rfr) / abs(mean_dd_pct)

def independent_metrics(initial_balance: float, start: date, stop: date, df: pl.DataFrame) -> dict:
    from Library.Portfolio.Position import PositionAPI
    gross_pnl_col = str(PositionAPI.ID.GrossPnL)
    comm_pnl_col = str(PositionAPI.ID.CommissionPnL)
    swap_pnl_col = str(PositionAPI.ID.SwapPnL)
    net_pnl_col = str(PositionAPI.ID.NetPnL)

    win_df, loss_df = split_winning_losing(df)
    total_n = calculate_total(df)
    total_points = calculate_sum(df, "Points")
    total_pips = calculate_sum(df, "Pips")
    
    win_n = calculate_total(win_df)
    win_points = calculate_sum(win_df, "Points")
    win_pips = calculate_sum(win_df, "Pips")
    
    loss_n = calculate_total(loss_df)
    loss_points = calculate_sum(loss_df, "Points")
    loss_pips = calculate_sum(loss_df, "Pips")
    
    win_rate = calculate_rate_perc(win_n, total_n)
    loss_rate = calculate_rate_perc(loss_n, total_n)
    
    win_max_trade, win_avg_trade, win_min_trade = calculate_min_avg_max(win_n, win_df, net_pnl_col)
    loss_min_trade, loss_avg_trade, loss_max_trade = calculate_min_avg_max(loss_n, loss_df, net_pnl_col)
    win_max_pts, win_avg_pts, win_min_pts = calculate_min_avg_max(win_n, win_df, "Points")
    loss_min_pts, loss_avg_pts, loss_max_pts = calculate_min_avg_max(loss_n, loss_df, "Points")
    win_max_pips, win_avg_pips, win_min_pips = calculate_min_avg_max(win_n, win_df, "Pips")
    loss_min_pips, loss_avg_pips, loss_max_pips = calculate_min_avg_max(loss_n, loss_df, "Pips")
    
    gross_pnl = calculate_sum(df, gross_pnl_col)
    comm_pnl = calculate_sum(df, comm_pnl_col)
    swap_pnl = calculate_sum(df, swap_pnl_col)
    win_pnl = calculate_sum(win_df, net_pnl_col)
    loss_pnl = calculate_sum(loss_df, net_pnl_col)
    total_pnl = calculate_sum(df, net_pnl_col)
    
    exp_win_ret, win_ret, win_vol = calculate_return_and_volatility(win_df)
    exp_loss_ret, loss_ret, loss_vol = calculate_return_and_volatility(loss_df)
    exp_net_ret, net_ret, net_vol = calculate_return_and_volatility(df)
    
    win_ret_ann = calculate_ann_return(start, stop, win_ret)
    win_vol_ann = calculate_ann_volatility(start, stop, win_vol)
    loss_ret_ann = calculate_ann_return(start, stop, loss_ret)
    loss_vol_ann = calculate_ann_volatility(start, stop, loss_vol)
    net_ret_ann = calculate_ann_return(start, stop, net_ret)
    net_vol_ann = calculate_ann_volatility(start, stop, net_vol)
    
    avg_trade = calculate_average(total_pnl, total_n)
    avg_points = calculate_average(total_points, total_n)
    avg_pips = calculate_average(total_pips, total_n)
    
    exp_trade = calculate_expected(win_rate, win_avg_trade, loss_rate, loss_avg_trade)
    exp_points = calculate_expected(win_rate, win_avg_pts, loss_rate, loss_avg_pts)
    exp_pips = calculate_expected(win_rate, win_avg_pips, loss_rate, loss_avg_pips)
    
    rr_ratio = calculate_risk_to_reward(win_avg_trade, loss_avg_trade)
    profit_factor = calculate_profit_factor(win_pnl, loss_pnl)
    
    max_dd_val, max_dd_pct, mean_dd_val, mean_dd_pct = calculate_drawdown(initial_balance, df)
    max_ru_val, max_ru_pct, mean_ru_val, mean_ru_pct = calculate_runup(initial_balance, df)
    
    max_hold, avg_hold, min_hold = calculate_holding_times(df, stop)
    
    sharpe = calculate_sharpe(net_ret_ann, net_vol_ann)
    sortino = calculate_sortino(net_ret_ann, loss_vol_ann)
    calmar = calculate_calmar(net_ret_ann, max_dd_pct)
    fitness = calculate_fitness(net_ret_ann, mean_dd_pct)
    
    return {
        TOTALTRADESVALUE: total_n,
        TOTALPOINTSVALUE: total_points,
        TOTALPIPSVALUE: total_pips,
            
        WINNINGTRADESVALUE: win_n,
        WINNINGPOINTSVALUE: win_points,
        WINNINGPIPSVALUE: win_pips,
        WINNINGRATEPERC: win_rate,
        MAXWINNINGTRADE: win_max_trade,
        AVERAGEWINNINGTRADE: win_avg_trade,
        MINWINNINGTRADE: win_min_trade,
        MAXWINNINGPOINTS: win_max_pts,
        AVERAGEWINNINGPOINTS: win_avg_pts,
        MINWINNINGPOINTS: win_min_pts,
        MAXWINNINGPIPS: win_max_pips,
        AVERAGEWINNINGPIPS: win_avg_pips,
        MINWINNINGPIPS: win_min_pips,
        EXPECTEDWINNINGRETURNPERC: exp_win_ret,
        WINNINGRETURNPERC: win_ret,
        WINNINGRETURNANNPERC: win_ret_ann,
        WINNINGVOLATILITYPERC: win_vol,
        WINNINGVOLATILITYANNPERC: win_vol_ann,

        LOSINGTRADESVALUE: loss_n,
        LOSINGPOINTSVALUE: loss_points,
        LOSINGPIPSVALUE: loss_pips,
        LOSINGRATEPERC: loss_rate,
        MAXLOSINGTRADE: loss_max_trade,
        AVERAGELOSINGTRADE: loss_avg_trade,
        MINLOSINGTRADE: loss_min_trade,
        MAXLOSINGPOINTS: loss_max_pts,
        AVERAGELOSINGPOINTS: loss_avg_pts,
        MINLOSINGPOINTS: loss_min_pts,
        MAXLOSINGPIPS: loss_max_pips,
        AVERAGELOSINGPIPS: loss_avg_pips,
        MINLOSINGPIPS: loss_min_pips,
        EXPECTEDLOSINGRETURNPERC: exp_loss_ret,
        LOSINGRETURNPERC: loss_ret,
        LOSINGRETURNANNPERC: loss_ret_ann,
        LOSINGVOLATILITYPERC: loss_vol,
        LOSINGVOLATILITYANNPERC: loss_vol_ann,

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
        EXPECTEDNETRETURNPERC: exp_net_ret,
        NETRETURNPERC: net_ret,
        NETRETURNANNPERC: net_ret_ann,
        NETVOLATILITYPERC: net_vol,
        NETVOLATILITYANNPERC: net_vol_ann,

        PROFITFACTOR: profit_factor,
        RISKTOREWARDRATIO: rr_ratio,
        MAXDRAWDOWNVALUE: max_dd_val,
        MAXDRAWDOWNPERC: max_dd_pct,
        MEANDRAWDOWNVALUE: mean_dd_val,
        MEANDRAWDOWNPERC: mean_dd_pct,
        MAXRUNUPVALUE: max_ru_val,
        MAXRUNUPPERC: max_ru_pct,
        MEANRUNUPVALUE: mean_ru_val,
        MEANRUNUPPERC: mean_ru_pct,
        MAXHOLDINGTIME: max_hold,
        AVERAGEHOLDINGTIME: avg_hold,
        MINHOLDINGTIME: min_hold,
        SHARPERATIO: sharpe,
        SORTINORATIO: sortino,
        CALMARRATIO: calmar,
        FITNESSRATIO: fitness
    }

def dependent_metrics(initial_balance: float, start: date, stop: date, df: pl.DataFrame, buy_col: str, sell_col: str, total_col: str) -> pl.DataFrame:
    from Library.Portfolio.Position import PositionAPI
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

    return pl.DataFrame({
        buy_col: [buy_metrics[k] for k in Metrics],
        sell_col: [sell_metrics[k] for k in Metrics],
        total_col: [total_metrics[k] for k in Metrics]
    }, strict=False)

def _safe_df(df: pl.DataFrame) -> pl.DataFrame:
    from Library.Portfolio.Position import PositionAPI
    from Library.Portfolio.Trade import TradeAPI
    if df.is_empty():
        required_cols = [
            str(PositionAPI.ID.UID), "Position", str(PositionAPI.ID.Direction), str(PositionAPI.ID.EntryTimestamp), str(TradeAPI.ID.ExitTimestamp), 
            str(PositionAPI.ID.EntryPrice), str(TradeAPI.ID.ExitPrice), str(PositionAPI.ID.Volume), "Points", "Pips", 
            str(PositionAPI.ID.GrossPnL), str(PositionAPI.ID.CommissionPnL), str(PositionAPI.ID.SwapPnL), str(PositionAPI.ID.NetPnL), 
            "DrawdownPoints", "DrawdownPips", "RunupPoints", "RunupPips", "NetReturn", "NetLogReturn", "DrawdownReturn", "NetReturnDrawdown", 
            str(PositionAPI.ID.EntryBalance), str(TradeAPI.ID.ExitBalance)
        ]
        schema = {col: pl.Float64() for col in required_cols}
        schema[str(PositionAPI.ID.EntryTimestamp)] = pl.Datetime()
        schema[str(TradeAPI.ID.ExitTimestamp)] = pl.Datetime()
        schema[str(PositionAPI.ID.Direction)] = pl.String()
        return pl.DataFrame(schema=schema)
    return df

def generate_realized_report(trades_df: pl.DataFrame, account: AccountAPI, start: date, stop: date) -> pl.DataFrame:
    initial_balance = account.Balance or 0.0
    safe_trades = _safe_df(trades_df)
    
    ind = sort_items(safe_trades)
    ind_df = dependent_metrics(initial_balance, start, stop, ind, REALIZED_BUY_INDIVIDUAL, REALIZED_SELL_INDIVIDUAL, REALIZED_TOTAL_INDIVIDUAL)
    agg = sort_items(aggregate_items(safe_trades))
    agg_df = dependent_metrics(initial_balance, start, stop, agg, REALIZED_BUY_AGGREGATED, REALIZED_SELL_AGGREGATED, REALIZED_TOTAL_AGGREGATED)
    
    labels_df = pl.DataFrame({STATISTICS_METRICS_LABEL: Metrics})
    return pl.concat([labels_df, ind_df, agg_df], how="horizontal")

def generate_unrealized_report(positions_df: pl.DataFrame, account: AccountAPI, start: date, stop: date) -> pl.DataFrame:
    initial_balance = account.Balance or 0.0
    safe_positions = _safe_df(positions_df)
    
    ind = sort_items(safe_positions)
    ind_df = dependent_metrics(initial_balance, start, stop, ind, UNREALIZED_BUY_INDIVIDUAL, UNREALIZED_SELL_INDIVIDUAL, UNREALIZED_TOTAL_INDIVIDUAL)
    agg = sort_items(aggregate_items(safe_positions))
    agg_df = dependent_metrics(initial_balance, start, stop, agg, UNREALIZED_BUY_AGGREGATED, UNREALIZED_SELL_AGGREGATED, UNREALIZED_TOTAL_AGGREGATED)
    
    labels_df = pl.DataFrame({STATISTICS_METRICS_LABEL: Metrics})
    return pl.concat([labels_df, ind_df, agg_df], how="horizontal")

def generate_net_report(trades_df: pl.DataFrame, positions_df: pl.DataFrame, account: AccountAPI, start: date, stop: date) -> pl.DataFrame:
    initial_balance = account.Balance or 0.0
    safe_trades = _safe_df(trades_df)
    safe_positions = _safe_df(positions_df)

    if not safe_trades.is_empty() and not safe_positions.is_empty():
        common_cols = set(safe_trades.columns).intersection(set(safe_positions.columns))
        net_df = pl.concat([safe_trades.select(list(common_cols)), safe_positions.select(list(common_cols))], how="vertical")
    elif not safe_trades.is_empty():
        net_df = safe_trades
    else:
        net_df = safe_positions

    ind = sort_items(net_df)
    ind_df = dependent_metrics(initial_balance, start, stop, ind, NET_BUY_INDIVIDUAL, NET_SELL_INDIVIDUAL, NET_TOTAL_INDIVIDUAL)
    agg = sort_items(aggregate_items(net_df))
    agg_df = dependent_metrics(initial_balance, start, stop, agg, NET_BUY_AGGREGATED, NET_SELL_AGGREGATED, NET_TOTAL_AGGREGATED)

    labels_df = pl.DataFrame({STATISTICS_METRICS_LABEL: Metrics})
    return pl.concat([labels_df, ind_df, agg_df], how="horizontal")