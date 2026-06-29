import math

from datetime import date, timedelta

from Library.Database.Dataframe import pl
from Library.Database import DatabaseAPI
from Library.Classes import Direction, Account, Trade
from Library.Manager import EPSILON

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

    def __init__(self):
        self._data : pl.DataFrame = DatabaseAPI.format_trade_data(None)        

    def update_data(self, trade: Trade) -> None:
        self._data.extend(DatabaseAPI.format_trade_data(trade))

    @staticmethod
    def sort_trades(trades_df: pl.DataFrame) -> pl.DataFrame:
        return trades_df.sort(by=Trade.ExitTimestamp, descending=False)

    @staticmethod
    def aggregate_trades(trades_df: pl.DataFrame) -> pl.DataFrame:
        return trades_df.group_by(Trade.PositionID).agg([
            pl.col(str(Trade.TradeID)),
            pl.col(str(Trade.PositionType)).first().alias(Trade.PositionType),
            pl.col(str(Trade.Direction)).first().alias(Trade.Direction),
            pl.col(str(Trade.EntryTimestamp)).min().alias(Trade.EntryTimestamp),
            pl.col(str(Trade.ExitTimestamp)).max().alias(Trade.ExitTimestamp),
            pl.col(str(Trade.EntryPrice)).first().alias(Trade.EntryPrice),
            pl.col(str(Trade.ExitPrice)).last().alias(Trade.ExitPrice),
            pl.col(str(Trade.Volume)).sum().alias(Trade.Volume),
            pl.col(str(Trade.Points)).sum().alias(Trade.Points),
            pl.col(str(Trade.Pips)).sum().alias(Trade.Pips),
            pl.col(str(Trade.GrossPnL)).sum().alias(Trade.GrossPnL),
            pl.col(str(Trade.CommissionPnL)).sum().alias(Trade.CommissionPnL),
            pl.col(str(Trade.SwapPnL)).sum().alias(Trade.SwapPnL),
            pl.col(str(Trade.NetPnL)).sum().alias(Trade.NetPnL),
            pl.col(str(Trade.DrawdownPoints)).min().alias(Trade.DrawdownPoints),
            pl.col(str(Trade.DrawdownPips)).min().alias(Trade.DrawdownPips),
            pl.col(str(Trade.DrawdownPnL)).min().alias(Trade.DrawdownPnL),
            pl.col(str(Trade.DrawdownReturn)).min().alias(Trade.DrawdownReturn),
            pl.col(str(Trade.NetReturn)).sum().alias(Trade.NetReturn),
            pl.col(str(Trade.NetLogReturn)).sum().alias(Trade.NetLogReturn),
            pl.col(str(Trade.ReturnOverMaxDrawdown)).sum().alias(Trade.ReturnOverMaxDrawdown),
            pl.col(str(Trade.BaseBalance)).first().alias(Trade.BaseBalance),
            pl.col(str(Trade.EntryBalance)).first().alias(Trade.EntryBalance),
            pl.col(str(Trade.ExitBalance)).last().alias(Trade.ExitBalance),
        ])

    @staticmethod
    def split_buy_sell_trades(trades_df: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame]:
        return (trades_df.filter(pl.col(str(Trade.Direction)) == Direction.Buy.name),
                trades_df.filter(pl.col(str(Trade.Direction)) == Direction.Sell.name))
    
    @staticmethod
    def split_winning_losing_trades(trades_df: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame]:
        return (trades_df.filter(pl.col(str(Trade.NetPnL)) > 0),
                trades_df.filter(pl.col(str(Trade.NetPnL)) <= 0))

    @staticmethod
    def calculate_total_trades(trades_df: pl.DataFrame) -> int:
        return trades_df.shape[0]
    
    @staticmethod
    def calculate_rate_perc(nr_cases: int, nr_trades: int) -> float:
        return (nr_cases / nr_trades) * 100 if nr_trades else 0.0
    
    @staticmethod
    def calculate_min_avg_max(nr_trades: int, trades_df: pl.DataFrame, column) -> tuple[float, float, float]:
        if nr_trades > 0:
            max_value = trades_df[column].max()
            avg_value = trades_df[column].mean()
            min_value = trades_df[column].min()
            return max_value, avg_value, min_value
        return 0.0, 0.0, 0.0
    
    @staticmethod
    def calculate_sum(trades_df: pl.DataFrame, column: str) -> float:
        return trades_df[column].sum()
    
    @staticmethod
    def calculate_average_value(net_value: float, nr_trades: int) -> float:
        return net_value / nr_trades if nr_trades else 0.0

    @staticmethod
    def calculate_expected_value(winning_perc: float, avg_winning_value: float, losing_perc: float, avg_losing_value: float) -> float:
        return (winning_perc / 100 * avg_winning_value) - (losing_perc / 100 * avg_losing_value)

    @staticmethod
    def calculate_return_and_volatility_perc(trades_df: pl.DataFrame) -> tuple[float, float, float]:
        expected_log_return = trades_df[str(Trade.NetLogReturn)].mean()
        total_log_return = trades_df[str(Trade.NetLogReturn)].sum()
        log_return_volatility = trades_df[str(Trade.NetLogReturn)].std()
        expected_return_perc = (math.exp(expected_log_return) - 1) * 100 if expected_log_return else 0.0
        total_return_perc = (math.exp(total_log_return) - 1) * 100 if total_log_return else 0.0
        return_volatility_perc = math.sqrt(math.exp(log_return_volatility**2) - 1) * 100 if log_return_volatility else 0.0
        return expected_return_perc, total_return_perc, return_volatility_perc

    @staticmethod
    def calculate_return_annualized_perc(start_timestamp: date, stop_timestamp: date, return_value_perc: float, trading_days: int = 365) -> float:
        if not return_value_perc:
            return 0.0
        days = (stop_timestamp - start_timestamp).days
        return (((1 + (return_value_perc / 100)) ** (trading_days / days)) - 1) * 100

    @staticmethod
    def calculate_volatility_annualized_perc(start_timestamp: date, stop_timestamp: date, volatility_value_perc: float, trading_days: int = 365) -> float:
        if not volatility_value_perc:
            return 0.0
        days = (stop_timestamp - start_timestamp).days
        return (volatility_value_perc / 100) * math.sqrt(trading_days / days) * 100
    
    @staticmethod
    def calculate_risk_to_reward(avg_winning_trade: float, avg_losing_trade: float)  -> float:
        return abs(avg_losing_trade) / avg_winning_trade if avg_winning_trade else 0.0
    
    @staticmethod
    def calculate_profit_factor(winning_pnl_value: float, losing_pnl_value: float) -> float:
        return winning_pnl_value / abs(losing_pnl_value) if losing_pnl_value else 0.0

    @staticmethod
    def calculate_max_and_mean_drawdown(initial_account: Account, trades_df: pl.DataFrame) -> tuple[float, float, float, float]:
        if trades_df.is_empty():
            return 0.0, 0.0, 0.0, 0.0
        initial_balance = initial_account.Balance
        cumulative_balance = trades_df[str(Trade.NetPnL)].cum_sum() + pl.Series([initial_balance])
        running_max = cumulative_balance.cum_max()
        drawdown = running_max - cumulative_balance
        max_drawdown_value = drawdown.max()
        cumulative_max = running_max.max()
        max_drawdown_perc = (max_drawdown_value / cumulative_max) * 100 if cumulative_max else 0.0
        mean_drawdown_value = drawdown.mean()
        mean_drawdown_perc = (mean_drawdown_value / cumulative_max) * 100 if cumulative_max else 0.0
        return max_drawdown_value, max_drawdown_perc, mean_drawdown_value, mean_drawdown_perc

    @staticmethod
    def calculate_holding_times(trades_df: pl.DataFrame) -> tuple[float, float, float]:
        if trades_df.is_empty():
            return 0.0, 0.0, 0.0
        holding_times: pl.Series = trades_df[str(Trade.ExitTimestamp)] - trades_df[str(Trade.EntryTimestamp)]
        def format_timedelta(td: timedelta):
            days = td.days
            hours = td.seconds // 3600
            return days + hours / 100
        max_holding_time = format_timedelta(holding_times.max())
        avg_holding_time = format_timedelta(holding_times.mean())
        min_holding_time = format_timedelta(holding_times.min())
        return max_holding_time, avg_holding_time, min_holding_time

    @staticmethod
    def calculate_sharpe_ratio(annualized_return_perc: float, annualized_volatility_perc: float, risk_free_rate: float = 0.0) -> float:
        annualized_volatility_perc = annualized_volatility_perc if annualized_volatility_perc else EPSILON
        return (annualized_return_perc - risk_free_rate) / annualized_volatility_perc

    @staticmethod
    def calculate_sortino_ratio(annualized_return_perc: float, downside_volatility_perc: float, risk_free_rate: float = 0.0) -> float:
        downside_volatility_perc = downside_volatility_perc if downside_volatility_perc else EPSILON
        return (annualized_return_perc - risk_free_rate) / downside_volatility_perc if downside_volatility_perc else 0.0

    @staticmethod
    def calculate_calmar_ratio(annualized_return_perc: float, max_drawdown_perc: float, risk_free_rate: float = 0.0) -> float:
        max_drawdown_perc = max_drawdown_perc if max_drawdown_perc else EPSILON
        return (annualized_return_perc - risk_free_rate) / abs(max_drawdown_perc) if max_drawdown_perc else 0.0

    @staticmethod
    def calculate_fitness_ratio(annualized_return_perc: float, mean_drawdown_perc: float, risk_free_rate: float = 0.0) -> float:
        mean_drawdown_perc = mean_drawdown_perc if mean_drawdown_perc else EPSILON
        return (annualized_return_perc - risk_free_rate) / abs(mean_drawdown_perc) if mean_drawdown_perc else 0.0

    def calculate_independent_metrics(self, initial_account: Account, start_timestamp: date, stop_timestamp: date, total_trades_df: pl.DataFrame) -> dict:
        winning_trades_df, losing_trades_df = self.split_winning_losing_trades(total_trades_df)
        total_nr_trades = self.calculate_total_trades(total_trades_df)
        total_points_value = self.calculate_sum(total_trades_df, str(Trade.Points))
        total_pips_value = self.calculate_sum(total_trades_df, str(Trade.Pips))
        winning_nr_trades = self.calculate_total_trades(winning_trades_df)
        winning_points_value = self.calculate_sum(winning_trades_df, str(Trade.Points))
        winning_pips_value = self.calculate_sum(winning_trades_df, str(Trade.Pips))
        losing_nr_trades = self.calculate_total_trades(losing_trades_df)
        losing_points_value = self.calculate_sum(losing_trades_df, str(Trade.Points))
        losing_pips_value = self.calculate_sum(losing_trades_df, str(Trade.Pips))
        winning_rate_perc = self.calculate_rate_perc(winning_nr_trades, total_nr_trades)
        losing_rate_perc = self.calculate_rate_perc(losing_nr_trades, total_nr_trades)
        winning_max_trade, winning_avg_trade, winning_min_trade = self.calculate_min_avg_max(winning_nr_trades, winning_trades_df, str(Trade.NetPnL))
        losing_min_trade, losing_avg_trade, losing_max_trade = self.calculate_min_avg_max(losing_nr_trades, losing_trades_df, str(Trade.NetPnL))
        winning_max_points, winning_avg_points, winning_min_points = self.calculate_min_avg_max(winning_nr_trades, winning_trades_df, str(Trade.Points))
        losing_min_points, losing_avg_points, losing_max_points = self.calculate_min_avg_max(losing_nr_trades, losing_trades_df, str(Trade.Points))
        winning_max_pips, winning_avg_pips, winning_min_pips = self.calculate_min_avg_max(winning_nr_trades, winning_trades_df, str(Trade.Pips))
        losing_min_pips, losing_avg_pips, losing_max_pips = self.calculate_min_avg_max(losing_nr_trades, losing_trades_df, str(Trade.Pips))
        gross_pnl_value = self.calculate_sum(total_trades_df, str(Trade.GrossPnL))
        commissions_value = self.calculate_sum(total_trades_df, str(Trade.CommissionPnL))
        swaps_value = self.calculate_sum(total_trades_df, str(Trade.SwapPnL))
        winning_pnl_value = self.calculate_sum(winning_trades_df, str(Trade.NetPnL))
        losing_pnl_value = self.calculate_sum(losing_trades_df, str(Trade.NetPnL))
        total_pnl_value = self.calculate_sum(total_trades_df, str(Trade.NetPnL))
        
        expected_winning_return_perc, winning_return_perc, winning_volatility_perc = self.calculate_return_and_volatility_perc(winning_trades_df)
        expected_losing_return_perc, losing_return_perc, losing_volatility_perc = self.calculate_return_and_volatility_perc(losing_trades_df)
        expected_net_return_perc, net_return_perc, net_volatility_perc = self.calculate_return_and_volatility_perc(total_trades_df)
        
        winning_return_annualized_perc = self.calculate_return_annualized_perc(start_timestamp, stop_timestamp, winning_return_perc)
        winning_volatility_annualized_perc = self.calculate_volatility_annualized_perc(start_timestamp, stop_timestamp, winning_volatility_perc)
        losing_return_annualized_perc = self.calculate_return_annualized_perc(start_timestamp, stop_timestamp, losing_return_perc)
        losing_volatility_annualized_perc = self.calculate_volatility_annualized_perc(start_timestamp, stop_timestamp, losing_volatility_perc)
        net_return_annualized_perc = self.calculate_return_annualized_perc(start_timestamp, stop_timestamp, net_return_perc)
        net_volatility_annualized_perc = self.calculate_volatility_annualized_perc(start_timestamp, stop_timestamp, net_volatility_perc)
        
        average_trade = self.calculate_average_value(total_pnl_value, total_nr_trades)
        average_points = self.calculate_average_value(total_points_value, total_nr_trades)
        average_pips = self.calculate_average_value(total_pips_value, total_nr_trades)
        expected_trade = self.calculate_expected_value(winning_rate_perc, winning_avg_trade, losing_rate_perc, losing_avg_trade)
        expected_points = self.calculate_expected_value(winning_rate_perc, winning_avg_points, losing_rate_perc, losing_avg_points)
        expected_pips = self.calculate_expected_value(winning_rate_perc, winning_avg_pips, losing_rate_perc, losing_avg_pips)
        
        risk_to_reward = self.calculate_risk_to_reward(winning_avg_trade, losing_avg_trade)
        profit_factor = self.calculate_profit_factor(winning_pnl_value, losing_pnl_value)
        max_drawdown_value, max_drawdown_perc, mean_drawdown_value, mean_drawdown_perc = self.calculate_max_and_mean_drawdown(initial_account, total_trades_df)
        max_holding_time, avg_holding_time, min_holding_time = self.calculate_holding_times(total_trades_df)
        
        sharpe_ratio = self.calculate_sharpe_ratio(net_return_annualized_perc, net_volatility_annualized_perc)
        sortino_ratio = self.calculate_sortino_ratio(net_return_annualized_perc, losing_volatility_annualized_perc)
        calmar_ratio = self.calculate_calmar_ratio(net_return_annualized_perc, max_drawdown_perc)
        fitness_ratio = self.calculate_fitness_ratio(net_return_annualized_perc, mean_drawdown_perc)
        
        return {
            self.TOTALTRADESVALUE: total_nr_trades,
            self.TOTALPOINTSVALUE: total_points_value,
            self.TOTALPIPSVALUE: total_pips_value,
                
            self.WINNINGTRADESVALUE: winning_nr_trades,
            self.WINNINGPOINTSVALUE: winning_points_value,
            self.WINNINGPIPSVALUE: winning_pips_value,
            self.WINNINGRATEPERC: winning_rate_perc,
            self.MAXWINNINGTRADE: winning_max_trade,
            self.AVERAGEWINNINGTRADE: winning_avg_trade,
            self.MINWINNINGTRADE: winning_min_trade,
            self.MAXWINNINGPOINTS: winning_max_points,
            self.AVERAGEWINNINGPOINTS: winning_avg_points,
            self.MINWINNINGPOINTS: winning_min_points,
            self.MAXWINNINGPIPS: winning_max_pips,
            self.AVERAGEWINNINGPIPS: winning_avg_pips,
            self.MINWINNINGPIPS: winning_min_pips,
            self.EXPECTEDWINNINGRETURNPERC: expected_winning_return_perc,
            self.WINNINGRETURNPERC: winning_return_perc,
            self.WINNINGRETURNANNPERC: winning_return_annualized_perc,
            self.WINNINGVOLATILITYPERC: winning_volatility_perc,
            self.WINNINGVOLATILITYANNPERC: winning_volatility_annualized_perc,

            self.LOSINGTRADESVALUE: losing_nr_trades,
            self.LOSINGPOINTSVALUE: losing_points_value,
            self.LOSINGPIPSVALUE: losing_pips_value,
            self.LOSINGRATEPERC: losing_rate_perc,
            self.MAXLOSINGTRADE: losing_max_trade,
            self.AVERAGELOSINGTRADE: losing_avg_trade,
            self.MINLOSINGTRADE: losing_min_trade,
            self.MAXLOSINGPOINTS: losing_max_points,
            self.AVERAGELOSINGPOINTS: losing_avg_points,
            self.MINLOSINGPOINTS: losing_min_points,
            self.MAXLOSINGPIPS: losing_max_pips,
            self.AVERAGELOSINGPIPS: losing_avg_pips,
            self.MINLOSINGPIPS: losing_min_pips,
            self.EXPECTEDLOSINGRETURNPERC: expected_losing_return_perc,
            self.LOSINGRETURNPERC: losing_return_perc,
            self.LOSINGRETURNANNPERC: losing_return_annualized_perc,
            self.LOSINGVOLATILITYPERC: losing_volatility_perc,
            self.LOSINGVOLATILITYANNPERC: losing_volatility_annualized_perc,

            self.AVERAGETRADE: average_trade,
            self.AVERAGEPOINTS: average_points,
            self.AVERAGEPIPS: average_pips,
            self.EXPECTEDTRADE: expected_trade,
            self.EXPECTEDPOINTS: expected_points,
            self.EXPECTEDPIPS: expected_pips,

            self.GROSSPNLVALUE:gross_pnl_value,
            self.COMMISSIONSPNLVALUE: commissions_value,
            self.SWAPSPNLVALUE: swaps_value,
            self.NETPNLVALUE: total_pnl_value,
            self.EXPECTEDNETRETURNPERC: expected_net_return_perc,
            self.NETRETURNPERC: net_return_perc,
            self.NETRETURNANNPERC: net_return_annualized_perc,
            self.NETVOLATILITYPERC: net_volatility_perc,
            self.NETVOLATILITYANNPERC: net_volatility_annualized_perc,

            self.PROFITFACTOR: profit_factor,
            self.RISKTOREWARDRATIO: risk_to_reward,
            self.MAXDRAWDOWNVALUE: max_drawdown_value,
            self.MAXDRAWDOWNPERC: max_drawdown_perc,
            self.MEANDRAWDOWNVALUE: mean_drawdown_value,
            self.MEANDRAWDOWNPERC: mean_drawdown_perc,
            self.MAXHOLDINGTIME: max_holding_time,
            self.AVERAGEHOLDINGTIME: avg_holding_time,
            self.MINHOLDINGTIME: min_holding_time,
            self.SHARPERATIO: sharpe_ratio,
            self.SORTINORATIO: sortino_ratio,
            self.CALMARRATIO: calmar_ratio,
            self.FITNESSRATIO: fitness_ratio
        }

    def calculate_dependent_metrics(self, initial_account: Account, start_timestamp: date, stop_timestamp: date, total_trades_df: pl.DataFrame, buy_metrics_label: str, sell_metrics_label: str, total_metrics_label: str) -> pl.DataFrame:
        buy_trades_df, sell_trades_df = self.split_buy_sell_trades(total_trades_df)
        buy_metrics_dict = self.calculate_independent_metrics(initial_account, start_timestamp, stop_timestamp, buy_trades_df)
        sell_metrics_dict = self.calculate_independent_metrics(initial_account, start_timestamp, stop_timestamp, sell_trades_df)
        total_metrics_dict = self.calculate_independent_metrics(initial_account, start_timestamp, stop_timestamp, total_trades_df)

        current_winning_streak = current_losing_streak = 0
        total_winning_streak = total_losing_streak = 0
        max_winning_streak_index = max_losing_streak_index = 0

        for idx, trade in enumerate(total_trades_df.iter_rows(named=True)):
            if trade[str(Trade.NetPnL)] > 0:
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
        buy_winning_streak_df, sell_winning_streak_df = self.split_buy_sell_trades(winning_streak_df)
        buy_metrics_dict[self.MAXWINNINGSTREAK] = self.calculate_total_trades(buy_winning_streak_df)
        sell_metrics_dict[self.MAXWINNINGSTREAK] = self.calculate_total_trades(sell_winning_streak_df)
        total_metrics_dict[self.MAXWINNINGSTREAK] = self.calculate_total_trades(winning_streak_df)

        losing_streak_df = total_trades_df.slice(offset=max_losing_streak_index - total_losing_streak + 1, length=total_losing_streak)
        buy_losing_streak_df, sell_losing_streak_df = self.split_buy_sell_trades(losing_streak_df)
        buy_metrics_dict[self.MAXLOSINGSTREAK] = self.calculate_total_trades(buy_losing_streak_df)
        sell_metrics_dict[self.MAXLOSINGSTREAK] = self.calculate_total_trades(sell_losing_streak_df)
        total_metrics_dict[self.MAXLOSINGSTREAK] = self.calculate_total_trades(losing_streak_df)

        buy_metrics_list = [buy_metrics_dict[key] for key in self.Metrics]
        sell_metrics_list = [sell_metrics_dict[key] for key in self.Metrics]
        total_metrics_list = [total_metrics_dict[key] for key in self.Metrics]

        return pl.DataFrame(data={buy_metrics_label: buy_metrics_list,
                                  sell_metrics_label: sell_metrics_list,
                                  total_metrics_label: total_metrics_list},
                            strict=False)

    def data(self, initial_account: Account, start_timestamp: date, stop_timestamp: date) -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
        statistical_metrics_df = pl.DataFrame(data=self.Metrics, schema={self.STATISTICS_METRICS_LABEL: pl.String()})
        individual_df = self.sort_trades(self._data)
        individual_metrics_df = self.calculate_dependent_metrics(initial_account, start_timestamp, stop_timestamp, individual_df, self.BUY_METRICS_INDIVIDUAL, self.SELL_METRICS_INDIVIDUAL, self.TOTAL_METRICS_INDIVIDUAL)
        aggregated_df = self.sort_trades(self.aggregate_trades(self._data))
        aggregated_metrics_df = self.calculate_dependent_metrics(initial_account, start_timestamp, stop_timestamp, aggregated_df, self.BUY_METRICS_AGGREGATED, self.SELL_METRICS_AGGREGATED, self.TOTAL_METRICS_AGGREGATED)
        return individual_df, aggregated_df, pl.concat([statistical_metrics_df, individual_metrics_df, aggregated_metrics_df], how="horizontal")