from __future__ import annotations

import math
from datetime import date, timedelta
from typing import Union, TYPE_CHECKING

from Library.Database.Dataframe import pl
from Library.Market.Price import Direction

if TYPE_CHECKING:
    from Library.Portfolio.Account import AccountAPI

class StatisticsAPI:

    STATISTICS_METRICS_LABEL = "Statistical Metrics"
    BUY_METRICS_INDIVIDUAL = "Buy Metrics (Individual)"
    SELL_METRICS_INDIVIDUAL = "Sell Metrics (Individual)"
    TOTAL_METRICS_INDIVIDUAL = "Total Metrics (Individual)"
    BUY_METRICS_AGGREGATED = "Buy Metrics (Aggregated)"
    SELL_METRICS_AGGREGATED = "Sell Metrics (Aggregated)"
    TOTAL_METRICS_AGGREGATED = "Total Metrics (Aggregated)"

    TOTALTRADESVALUE = "Nr Total of Trades"
    TOTALPOINTSVALUE = "Total Points"
    TOTALPIPSVALUE = "Total Pips"

    WINNINGTRADESVALUE = "Nr of Winning Trades"
    WINNINGPOINTSVALUE = "Winning Points"
    WINNINGPIPSVALUE = "Winning Pips"
    WINNINGRATEPERC = "Winning Rate (%)"
    MAXWINNINGTRADE = "Max Winning Trade (€)"
    AVERAGEWINNINGTRADE = "Avg Winning Trade (€)"
    MINWINNINGTRADE = "Min Winning Trade (€)"
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
    MAXLOSINGTRADE = "Max Losing Trade (€)"
    AVERAGELOSINGTRADE = "Avg Losing Trade (€)"
    MINLOSINGTRADE = "Min Losing Trade (€)"
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

    AVERAGETRADE = "Average Trade (€) [Backward]"
    AVERAGEPOINTS = "Average Points [Backward]"
    AVERAGEPIPS = "Average Pips [Backward]"
    EXPECTEDTRADE = "Expected Trade (€) [Forward]"
    EXPECTEDPOINTS = "Expected Points [Forward]"
    EXPECTEDPIPS = "Expected Pips [Forward]"

    GROSSPNLVALUE = "Gross Profit/Loss (€)"
    COMMISSIONSPNLVALUE = "Commissions Profit/Loss (€)"
    SWAPSPNLVALUE = "Swaps Profit/Loss (€)"
    NETPNLVALUE = "Net Profit/Loss (€)"
    EXPECTEDNETRETURNPERC = "Expected Net Return (%)"
    NETRETURNPERC = "Net Return (%)"
    NETRETURNANNPERC = "Net Return Annualised (%) [µ]"
    NETVOLATILITYPERC = "Net Volatility (%)"
    NETVOLATILITYANNPERC = "Net Volatility Annualised (%) [σ]"

    PROFITFACTOR = "Profit Factor"
    RISKTOREWARDRATIO = "Risk-to-Reward Ratio"
    MAXDRAWDOWNVALUE = "Max Drawdown (€)"
    MAXDRAWDOWNPERC = "Max Drawdown (%)"
    MEANDRAWDOWNVALUE = "Mean Drawdown (€)"
    MEANDRAWDOWNPERC = "Mean Drawdown (%)"
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
        MAXHOLDINGTIME,
        AVERAGEHOLDINGTIME,
        MINHOLDINGTIME,
        SHARPERATIO,
        SORTINORATIO,
        CALMARRATIO,
        FITNESSRATIO
    ]

    @staticmethod
    def sort_trades(trades_df: pl.DataFrame) -> pl.DataFrame:
        if trades_df.is_empty() or "ExitTimestamp" not in trades_df.columns: return trades_df
        return trades_df.sort(by="ExitTimestamp", descending=False)

    @staticmethod
    def aggregate_trades(trades_df: pl.DataFrame) -> pl.DataFrame:
        if trades_df.is_empty(): return trades_df
        return trades_df.group_by("Position").agg([
            pl.col("UID").first(),
            pl.col("Type").first(),
            pl.col("Direction").first(),
            pl.col("EntryTimestamp").min(),
            pl.col("ExitTimestamp").max(),
            pl.col("EntryPrice").first(),
            pl.col("ExitPrice").last(),
            pl.col("Volume").sum(),
            pl.col("Points").sum(),
            pl.col("Pips").sum(),
            pl.col("GrossPnL").sum(),
            pl.col("CommissionPnL").sum(),
            pl.col("SwapPnL").sum(),
            pl.col("NetPnL").sum(),
            pl.col("DrawdownPoints").min(),
            pl.col("DrawdownPips").min(),
            pl.col("DrawdownPnL").min(),
            pl.col("DrawdownReturn").min(),
            pl.col("NetReturn").sum(),
            pl.col("NetLogReturn").sum(),
            pl.col("ReturnOverMaxDrawdown").sum(),
            pl.col("BaseBalance").first(),
            pl.col("EntryBalance").first(),
            pl.col("ExitBalance").last(),
        ])

    @staticmethod
    def split_buy_sell_trades(trades_df: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame]:
        if trades_df.is_empty() or "Direction" not in trades_df.columns: return trades_df, trades_df
        return (trades_df.filter(pl.col("Direction") == Direction.Buy.name),
                trades_df.filter(pl.col("Direction") == Direction.Sell.name))
    
    @staticmethod
    def split_winning_losing_trades(trades_df: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame]:
        if trades_df.is_empty() or "NetPnL" not in trades_df.columns: return trades_df, trades_df
        return (trades_df.filter(pl.col("NetPnL") > 0),
                trades_df.filter(pl.col("NetPnL") <= 0))

    @staticmethod
    def calculate_total_trades(trades_df: pl.DataFrame) -> int:
        return trades_df.shape[0] if not trades_df.is_empty() else 0
    
    @staticmethod
    def calculate_rate_perc(nr_cases: int, nr_trades: int) -> float:
        return (nr_cases / nr_trades) * 100 if nr_trades else 0.0
    
    @staticmethod
    def calculate_min_avg_max(nr_trades: int, trades_df: pl.DataFrame, column: str) -> tuple[float, float, float]:
        if nr_trades > 0 and column in trades_df.columns:
            return trades_df[column].max(), trades_df[column].mean(), trades_df[column].min()
        return 0.0, 0.0, 0.0
    
    @staticmethod
    def calculate_sum(trades_df: pl.DataFrame, column: str) -> float:
        return trades_df[column].sum() if not trades_df.is_empty() and column in trades_df.columns else 0.0
    
    @staticmethod
    def calculate_average_value(net_value: float, nr_trades: int) -> float:
        return net_value / nr_trades if nr_trades else 0.0

    @staticmethod
    def calculate_expected_value(winning_perc: float, avg_winning_value: float, losing_perc: float, avg_losing_value: float) -> float:
        return (winning_perc / 100 * avg_winning_value) - (losing_perc / 100 * avg_losing_value)

    @staticmethod
    def calculate_return_and_volatility_perc(trades_df: pl.DataFrame) -> tuple[float, float, float]:
        if trades_df.is_empty() or "NetLogReturn" not in trades_df.columns: return 0.0, 0.0, 0.0
        exp_log = trades_df["NetLogReturn"].mean()
        tot_log = trades_df["NetLogReturn"].sum()
        vol_log = trades_df["NetLogReturn"].std()
        exp_ret = (math.exp(exp_log) - 1) * 100 if exp_log else 0.0
        tot_ret = (math.exp(tot_log) - 1) * 100 if tot_log else 0.0
        vol_ret = math.sqrt(math.exp((vol_log or 0)**2) - 1) * 100 if vol_log else 0.0
        return exp_ret, tot_ret, vol_ret

    @staticmethod
    def calculate_return_annualized_perc(start: date, stop: date, ret_perc: float, days: int = 365) -> float:
        if not ret_perc or not start or not stop: return 0.0
        delta = (stop - start).days
        if delta <= 0: return 0.0
        return (((1 + (ret_perc / 100)) ** (days / delta)) - 1) * 100

    @staticmethod
    def calculate_volatility_annualized_perc(start: date, stop: date, vol_perc: float, days: int = 365) -> float:
        if not vol_perc or not start or not stop: return 0.0
        delta = (stop - start).days
        if delta <= 0: return 0.0
        return (vol_perc / 100) * math.sqrt(days / delta) * 100
    
    @staticmethod
    def calculate_risk_to_reward(avg_win: float, avg_loss: float) -> float:
        return abs(avg_loss) / avg_win if avg_win else 0.0
    
    @staticmethod
    def calculate_profit_factor(win_pnl: float, loss_pnl: float) -> float:
        return win_pnl / abs(loss_pnl) if loss_pnl else 0.0

    @staticmethod
    def calculate_max_and_mean_drawdown(initial_acc: AccountAPI, trades_df: pl.DataFrame) -> tuple[float, float, float, float]:
        if trades_df.is_empty() or "NetPnL" not in trades_df.columns: return 0.0, 0.0, 0.0, 0.0
        init_bal = initial_acc.Balance or 0.0
        cum_bal = trades_df["NetPnL"].cum_sum() + init_bal
        run_max = cum_bal.cum_max()
        dd = run_max - cum_bal
        max_dd_val = dd.max()
        cum_max = run_max.max()
        max_dd_pct = (max_dd_val / cum_max) * 100 if cum_max else 0.0
        mean_dd_val = dd.mean()
        mean_dd_pct = (mean_dd_val / cum_max) * 100 if cum_max else 0.0
        return max_dd_val, max_dd_pct, mean_dd_val, mean_dd_pct

    @staticmethod
    def calculate_holding_times(trades_df: pl.DataFrame) -> tuple[float, float, float]:
        if trades_df.is_empty() or "ExitTimestamp" not in trades_df.columns or "EntryTimestamp" not in trades_df.columns: return 0.0, 0.0, 0.0
        h_times = trades_df["ExitTimestamp"] - trades_df["EntryTimestamp"]
        def fmt(td: timedelta): return td.days + (td.seconds // 3600) / 100 if td else 0.0
        return fmt(h_times.max()), fmt(h_times.mean()), fmt(h_times.min())

    @staticmethod
    def calculate_sharpe_ratio(annualized_return_perc: float, annualized_volatility_perc: float, risk_free_rate: float = 0.0) -> float:
        annualized_volatility_perc = annualized_volatility_perc if annualized_volatility_perc else 1e-2
        return (annualized_return_perc - risk_free_rate) / annualized_volatility_perc

    @staticmethod
    def calculate_sortino_ratio(annualized_return_perc: float, downside_volatility_perc: float, risk_free_rate: float = 0.0) -> float:
        downside_volatility_perc = downside_volatility_perc if downside_volatility_perc else 1e-2
        return (annualized_return_perc - risk_free_rate) / downside_volatility_perc if downside_volatility_perc else 0.0

    @staticmethod
    def calculate_calmar_ratio(annualized_return_perc: float, max_drawdown_perc: float, risk_free_rate: float = 0.0) -> float:
        max_drawdown_perc = max_drawdown_perc if max_drawdown_perc else 1e-2
        return (annualized_return_perc - risk_free_rate) / abs(max_drawdown_perc) if max_drawdown_perc else 0.0

    @staticmethod
    def calculate_fitness_ratio(annualized_return_perc: float, mean_drawdown_perc: float, risk_free_rate: float = 0.0) -> float:
        mean_drawdown_perc = mean_drawdown_perc if mean_drawdown_perc else 1e-2
        return (annualized_return_perc - risk_free_rate) / abs(mean_drawdown_perc) if mean_drawdown_perc else 0.0

    @classmethod
    def calculate_independent_metrics(cls, initial_acc: AccountAPI, start: date, stop: date, total_trades_df: pl.DataFrame) -> dict:
        winning_trades_df, losing_trades_df = cls.split_winning_losing_trades(total_trades_df)
        total_nr_trades = cls.calculate_total_trades(total_trades_df)
        total_points_value = cls.calculate_sum(total_trades_df, "Points")
        total_pips_value = cls.calculate_sum(total_trades_df, "Pips")
        winning_nr_trades = cls.calculate_total_trades(winning_trades_df)
        winning_points_value = cls.calculate_sum(winning_trades_df, "Points")
        winning_pips_value = cls.calculate_sum(winning_trades_df, "Pips")
        losing_nr_trades = cls.calculate_total_trades(losing_trades_df)
        losing_points_value = cls.calculate_sum(losing_trades_df, "Points")
        losing_pips_value = cls.calculate_sum(losing_trades_df, "Pips")
        winning_rate_perc = cls.calculate_rate_perc(winning_nr_trades, total_nr_trades)
        losing_rate_perc = cls.calculate_rate_perc(losing_nr_trades, total_nr_trades)
        winning_max_trade, winning_avg_trade, winning_min_trade = cls.calculate_min_avg_max(winning_nr_trades, winning_trades_df, "NetPnL")
        losing_min_trade, losing_avg_trade, losing_max_trade = cls.calculate_min_avg_max(losing_nr_trades, losing_trades_df, "NetPnL")
        winning_max_points, winning_avg_points, winning_min_points = cls.calculate_min_avg_max(winning_nr_trades, winning_trades_df, "Points")
        losing_min_points, losing_avg_points, losing_max_points = cls.calculate_min_avg_max(losing_nr_trades, losing_trades_df, "Points")
        winning_max_pips, winning_avg_pips, winning_min_pips = cls.calculate_min_avg_max(winning_nr_trades, winning_trades_df, "Pips")
        losing_min_pips, losing_avg_pips, losing_max_pips = cls.calculate_min_avg_max(losing_nr_trades, losing_trades_df, "Pips")
        gross_pnl_value = cls.calculate_sum(total_trades_df, "GrossPnL")
        commissions_value = cls.calculate_sum(total_trades_df, "CommissionPnL")
        swaps_value = cls.calculate_sum(total_trades_df, "SwapPnL")
        winning_pnl_value = cls.calculate_sum(winning_trades_df, "NetPnL")
        losing_pnl_value = cls.calculate_sum(losing_trades_df, "NetPnL")
        total_pnl_value = cls.calculate_sum(total_trades_df, "NetPnL")
        
        expected_winning_return_perc, winning_return_perc, winning_volatility_perc = cls.calculate_return_and_volatility_perc(winning_trades_df)
        expected_losing_return_perc, losing_return_perc, losing_volatility_perc = cls.calculate_return_and_volatility_perc(losing_trades_df)
        expected_net_return_perc, net_return_perc, net_volatility_perc = cls.calculate_return_and_volatility_perc(total_trades_df)
        
        winning_return_annualized_perc = cls.calculate_return_annualized_perc(start, stop, winning_return_perc)
        winning_volatility_annualized_perc = cls.calculate_volatility_annualized_perc(start, stop, winning_volatility_perc)
        losing_return_annualized_perc = cls.calculate_return_annualized_perc(start, stop, losing_return_perc)
        losing_volatility_annualized_perc = cls.calculate_volatility_annualized_perc(start, stop, losing_volatility_perc)
        net_return_annualized_perc = cls.calculate_return_annualized_perc(start, stop, net_return_perc)
        net_volatility_annualized_perc = cls.calculate_volatility_annualized_perc(start, stop, net_volatility_perc)
        
        average_trade = cls.calculate_average_value(total_pnl_value, total_nr_trades)
        average_points = cls.calculate_average_value(total_points_value, total_nr_trades)
        average_pips = cls.calculate_average_value(total_pips_value, total_nr_trades)
        expected_trade = cls.calculate_expected_value(winning_rate_perc, winning_avg_trade, losing_rate_perc, losing_avg_trade)
        expected_points = cls.calculate_expected_value(winning_rate_perc, winning_avg_points, losing_rate_perc, losing_avg_points)
        expected_pips = cls.calculate_expected_value(winning_rate_perc, winning_avg_pips, losing_rate_perc, losing_avg_pips)
        
        risk_to_reward = cls.calculate_risk_to_reward(winning_avg_trade, losing_avg_trade)
        profit_factor = cls.calculate_profit_factor(winning_pnl_value, losing_pnl_value)
        max_drawdown_value, max_drawdown_perc, mean_drawdown_value, mean_drawdown_perc = cls.calculate_max_and_mean_drawdown(initial_acc, total_trades_df)
        max_holding_time, avg_holding_time, min_holding_time = cls.calculate_holding_times(total_trades_df)
        
        sharpe_ratio = cls.calculate_sharpe_ratio(net_return_annualized_perc, net_volatility_annualized_perc)
        sortino_ratio = cls.calculate_sortino_ratio(net_return_annualized_perc, losing_volatility_annualized_perc)
        calmar_ratio = cls.calculate_calmar_ratio(net_return_annualized_perc, max_drawdown_perc)
        fitness_ratio = cls.calculate_fitness_ratio(net_return_annualized_perc, mean_drawdown_perc)
        
        return {
            cls.TOTALTRADESVALUE: total_nr_trades,
            cls.TOTALPOINTSVALUE: total_points_value,
            cls.TOTALPIPSVALUE: total_pips_value,
                
            cls.WINNINGTRADESVALUE: winning_nr_trades,
            cls.WINNINGPOINTSVALUE: winning_points_value,
            cls.WINNINGPIPSVALUE: winning_pips_value,
            cls.WINNINGRATEPERC: winning_rate_perc,
            cls.MAXWINNINGTRADE: winning_max_trade,
            cls.AVERAGEWINNINGTRADE: winning_avg_trade,
            cls.MINWINNINGTRADE: winning_min_trade,
            cls.MAXWINNINGPOINTS: winning_max_points,
            cls.AVERAGEWINNINGPOINTS: winning_avg_points,
            cls.MINWINNINGPOINTS: winning_min_points,
            cls.MAXWINNINGPIPS: winning_max_pips,
            cls.AVERAGEWINNINGPIPS: winning_avg_pips,
            cls.MINWINNINGPIPS: winning_min_pips,
            cls.EXPECTEDWINNINGRETURNPERC: expected_winning_return_perc,
            cls.WINNINGRETURNPERC: winning_return_perc,
            cls.WINNINGRETURNANNPERC: winning_return_annualized_perc,
            cls.WINNINGVOLATILITYPERC: winning_volatility_perc,
            cls.WINNINGVOLATILITYANNPERC: winning_volatility_annualized_perc,

            cls.LOSINGTRADESVALUE: losing_nr_trades,
            cls.LOSINGPOINTSVALUE: losing_points_value,
            cls.LOSINGPIPSVALUE: losing_pips_value,
            cls.LOSINGRATEPERC: losing_rate_perc,
            cls.MAXLOSINGTRADE: losing_max_trade,
            cls.AVERAGELOSINGTRADE: losing_avg_trade,
            cls.MINLOSINGTRADE: losing_min_trade,
            cls.MAXLOSINGPOINTS: losing_max_points,
            cls.AVERAGELOSINGPOINTS: losing_avg_points,
            cls.MINLOSINGPOINTS: losing_min_points,
            cls.MAXLOSINGPIPS: losing_max_pips,
            cls.AVERAGELOSINGPIPS: losing_avg_pips,
            cls.MINLOSINGPIPS: losing_min_pips,
            cls.EXPECTEDLOSINGRETURNPERC: expected_losing_return_perc,
            cls.LOSINGRETURNPERC: losing_return_perc,
            cls.LOSINGRETURNANNPERC: losing_return_annualized_perc,
            cls.LOSINGVOLATILITYPERC: losing_volatility_perc,
            cls.LOSINGVOLATILITYANNPERC: losing_volatility_annualized_perc,

            cls.AVERAGETRADE: average_trade,
            cls.AVERAGEPOINTS: average_points,
            cls.AVERAGEPIPS: average_pips,
            cls.EXPECTEDTRADE: expected_trade,
            cls.EXPECTEDPOINTS: expected_points,
            cls.EXPECTEDPIPS: expected_pips,

            cls.GROSSPNLVALUE: gross_pnl_value,
            cls.COMMISSIONSPNLVALUE: commissions_value,
            cls.SWAPSPNLVALUE: swaps_value,
            cls.NETPNLVALUE: total_pnl_value,
            cls.EXPECTEDNETRETURNPERC: expected_net_return_perc,
            cls.NETRETURNPERC: net_return_perc,
            cls.NETRETURNANNPERC: net_return_annualized_perc,
            cls.NETVOLATILITYPERC: net_volatility_perc,
            cls.NETVOLATILITYANNPERC: net_volatility_annualized_perc,

            cls.PROFITFACTOR: profit_factor,
            cls.RISKTOREWARDRATIO: risk_to_reward,
            cls.MAXDRAWDOWNVALUE: max_drawdown_value,
            cls.MAXDRAWDOWNPERC: max_drawdown_perc,
            cls.MEANDRAWDOWNVALUE: mean_drawdown_value,
            cls.MEANDRAWDOWNPERC: mean_drawdown_perc,
            cls.MAXHOLDINGTIME: max_holding_time,
            cls.AVERAGEHOLDINGTIME: avg_holding_time,
            cls.MINHOLDINGTIME: min_holding_time,
            cls.SHARPERATIO: sharpe_ratio,
            cls.SORTINORATIO: sortino_ratio,
            cls.CALMARRATIO: calmar_ratio,
            cls.FITNESSRATIO: fitness_ratio
        }

    @classmethod
    def calculate_dependent_metrics(cls, initial_acc: AccountAPI, start: date, stop: date, total_trades_df: pl.DataFrame, buy_metrics_label: str, sell_metrics_label: str, total_metrics_label: str) -> pl.DataFrame:
        buy_trades_df, sell_trades_df = cls.split_buy_sell_trades(total_trades_df)
        buy_metrics_dict = cls.calculate_independent_metrics(initial_acc, start, stop, buy_trades_df)
        sell_metrics_dict = cls.calculate_independent_metrics(initial_acc, start, stop, sell_trades_df)
        total_metrics_dict = cls.calculate_independent_metrics(initial_acc, start, stop, total_trades_df)

        current_winning_streak = current_losing_streak = 0
        total_winning_streak = total_losing_streak = 0
        max_winning_streak_index = max_losing_streak_index = 0

        if not total_trades_df.is_empty() and "NetPnL" in total_trades_df.columns:
            for idx, row in enumerate(total_trades_df.iter_rows(named=True)):
                if row.get("NetPnL", 0) > 0:
                    current_winning_streak += 1
                    current_losing_streak = 0
                else:
                    current_losing_streak += 1
                    current_winning_streak = 0

                if current_winning_streak > total_winning_streak:
                    max_winning_streak_index = idx
                    total_winning_streak = current_winning_streak
                if current_losing_streak > total_losing_streak:
                    max_losing_streak_index = idx
                    total_losing_streak = current_losing_streak

            winning_streak_df = total_trades_df.slice(offset=max_winning_streak_index - total_winning_streak + 1, length=total_winning_streak)
            buy_winning_streak_df, sell_winning_streak_df = cls.split_buy_sell_trades(winning_streak_df)
            buy_metrics_dict[cls.MAXWINNINGSTREAK] = cls.calculate_total_trades(buy_winning_streak_df)
            sell_metrics_dict[cls.MAXWINNINGSTREAK] = cls.calculate_total_trades(sell_winning_streak_df)
            total_metrics_dict[cls.MAXWINNINGSTREAK] = cls.calculate_total_trades(winning_streak_df)

            losing_streak_df = total_trades_df.slice(offset=max_losing_streak_index - total_losing_streak + 1, length=total_losing_streak)
            buy_losing_streak_df, sell_losing_streak_df = cls.split_buy_sell_trades(losing_streak_df)
            buy_metrics_dict[cls.MAXLOSINGSTREAK] = cls.calculate_total_trades(buy_losing_streak_df)
            sell_metrics_dict[cls.MAXLOSINGSTREAK] = cls.calculate_total_trades(sell_losing_streak_df)
            total_metrics_dict[cls.MAXLOSINGSTREAK] = cls.calculate_total_trades(losing_streak_df)
        else:
            buy_metrics_dict[cls.MAXWINNINGSTREAK] = 0
            sell_metrics_dict[cls.MAXWINNINGSTREAK] = 0
            total_metrics_dict[cls.MAXWINNINGSTREAK] = 0
            buy_metrics_dict[cls.MAXLOSINGSTREAK] = 0
            sell_metrics_dict[cls.MAXLOSINGSTREAK] = 0
            total_metrics_dict[cls.MAXLOSINGSTREAK] = 0

        buy_metrics_list = [buy_metrics_dict[key] for key in cls.Metrics]
        sell_metrics_list = [sell_metrics_dict[key] for key in cls.Metrics]
        total_metrics_list = [total_metrics_dict[key] for key in cls.Metrics]

        return pl.DataFrame(data={buy_metrics_label: buy_metrics_list,
                                  sell_metrics_label: sell_metrics_list,
                                  total_metrics_label: total_metrics_list},
                            strict=False)

    @classmethod
    def data(cls, data: pl.DataFrame, initial_acc: AccountAPI, start: date, stop: date) -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
        statistical_metrics_df = pl.DataFrame(data=cls.Metrics, schema={cls.STATISTICS_METRICS_LABEL: pl.String()})
        individual_df = cls.sort_trades(data)
        individual_metrics_df = cls.calculate_dependent_metrics(initial_acc, start, stop, individual_df, cls.BUY_METRICS_INDIVIDUAL, cls.SELL_METRICS_INDIVIDUAL, cls.TOTAL_METRICS_INDIVIDUAL)
        aggregated_df = cls.sort_trades(cls.aggregate_trades(data))
        aggregated_metrics_df = cls.calculate_dependent_metrics(initial_acc, start, stop, aggregated_df, cls.BUY_METRICS_AGGREGATED, cls.SELL_METRICS_AGGREGATED, cls.TOTAL_METRICS_AGGREGATED)
        return individual_df, aggregated_df, pl.concat([statistical_metrics_df, individual_metrics_df, aggregated_metrics_df], how="horizontal")