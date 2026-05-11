import os
from typing import Union, Type
from pathlib import Path
from argparse import ArgumentParser

from Library.Database.Dataframe import pl
from Library.Logging import *
from Library.Classes import VerboseType, AssetType, SpreadType, CommissionType, SwapType, SystemType, StrategyType
from Library.Parameters import ParametersAPI, Parameters
from Library.Utils import timer

from Library.Portfolio import StatisticsAPI
from Library.Strategy import *
from Library.System import *

pl.Config.set_tbl_cols(-1)
pl.Config.set_tbl_rows(-1)
pl.Config.set_tbl_width_chars(-1)
pl.Config.set_fmt_str_lengths(1000)
pl.Config.set_fmt_table_cell_list_len(-1)

execution = Path(__file__).parent.name

parameterise: ParametersAPI = ParametersAPI()

base_parser = ArgumentParser(add_help=False)
base_parser.add_argument("--console", type=str, required=True, choices=[_.name for _ in VerboseType])
base_parser.add_argument("--telegram", type=str, required=True, choices=[_.name for _ in VerboseType])
base_parser.add_argument("--file", type=str, required=True, choices=[_.name for _ in VerboseType])
base_parser.add_argument("--strategy", type=str, required=True, choices=[_.name for _ in StrategyType])
base_parser.add_argument("--broker", type=str, required=True, choices=parameterise.Watchlist.Brokers)
base_parser.add_argument("--group", type=str, required=True, choices=parameterise.Watchlist.Symbols.keys())
base_parser.add_argument("--symbol", type=str, required=True, choices=[s for g in parameterise.Watchlist.Symbols.values() for s in g])
base_parser.add_argument("--timeframe", type=str, required=True, choices=parameterise.Watchlist.Timeframes)

period_parser = ArgumentParser(add_help=False)
period_parser.add_argument("--start", type=str, required=True)
period_parser.add_argument("--stop", type=str, required=True)

account_parser = ArgumentParser(add_help=False)
account_parser.add_argument("--account-asset", type=str, required=True, choices=[_.name for _ in AssetType])
account_parser.add_argument("--account-balance", type=float, required=True)
account_parser.add_argument("--account-leverage", type=float, required=True)

fee_parser = ArgumentParser(add_help=False)
fee_parser.add_argument("--spread-type", type=str, required=True, choices=[_.name for _ in SpreadType])
fee_parser.add_argument("--spread-value", type=float, required=False, default=None)
fee_parser.add_argument("--commission-type", type=str, required=True, choices=[_.name for _ in CommissionType])
fee_parser.add_argument("--commission-value", type=float, required=False, default=None)
fee_parser.add_argument("--swap-type", type=str, required=True, choices=[_.name for _ in SwapType])
fee_parser.add_argument("--swap-buy", type=float, required=False, default=None)
fee_parser.add_argument("--swap-sell", type=float, required=False, default=None)

parser = ArgumentParser()
system_parser = parser.add_subparsers(dest="system", required=True)

backtesting_parser = system_parser.add_parser(SystemType.Backtesting.name, parents=[base_parser, period_parser, account_parser, fee_parser])

optimization_parser = system_parser.add_parser(SystemType.Optimization.name, parents=[base_parser, period_parser, account_parser, fee_parser])
optimization_parser.add_argument("--training", type=int, required=True)
optimization_parser.add_argument("--validation", type=int, required=True)
optimization_parser.add_argument("--testing", type=int, required=True)
optimization_parser.add_argument("--fitness", type=str, required=True, choices=StatisticsAPI.Metrics)
optimization_parser.add_argument("--threads", type=int, required=False, default=os.cpu_count())

learning_parser = system_parser.add_parser(SystemType.Learning.name, parents=[base_parser, period_parser, account_parser, fee_parser])
learning_parser.add_argument("--reward", type=str, required=True, choices=StatisticsAPI.Metrics)
learning_parser.add_argument("--episodes", type=int, required=True)

args = parser.parse_args()

LoggingAPI.init(
    System=args.system,
    Strategy=args.strategy,
    Broker=args.broker,
    Group=args.group,
    Symbol=args.symbol,
    Timeframe=args.timeframe
)

ConsoleAPI.setup(VerboseType(VerboseType[args.console]))
TelegramAPI.setup(VerboseType(VerboseType[args.telegram]), uid=args.group)
FileAPI.setup(VerboseType(VerboseType[args.file]), uid=[execution, args.system])

log = HandlerAPI(Class=execution, Subclass="Execution Management")

@timer
@log.guard
def main():

    strategy: Union[Type[StrategyAPI], None] = None
    match args.strategy:
        case StrategyType.Download.name:
            strategy = DownloadStrategyAPI
        case StrategyType.NNFX.name:
            strategy = NNFXStrategyAPI
        case StrategyType.DDPG.name:
            strategy = DDPGStrategyAPI

    parameters: Parameters = parameterise[args.broker][args.group][args.symbol][args.timeframe]

    system: Union[SystemAPI, None] = None
    match args.system:
        case SystemType.Backtesting.name:
            params: Parameters = parameters.Backtesting[args.strategy]
            system = BacktestingSystemAPI(
                broker=args.broker,
                group=args.group,
                symbol=args.symbol,
                timeframe=args.timeframe,
                strategy=strategy,
                parameters=params,
                start=args.start,
                stop=args.stop,
                account=(AssetType(AssetType[args.account_asset]), args.account_balance, args.account_leverage),
                spread=(SpreadType(SpreadType[args.spread_type]), args.spread_value),
                commission=(CommissionType(CommissionType[args.commission_type]), args.commission_value),
                swap=(SwapType(SwapType[args.swap_type]), args.swap_buy, args.swap_sell)
            )
        case SystemType.Optimization.name:
            params: Parameters = parameters.Backtesting[args.strategy]
            config: Parameters = parameters.Optimization[args.strategy]
            system = OptimizationSystemAPI(
                broker=args.broker,
                group=args.group,
                symbol=args.symbol,
                timeframe=args.timeframe,
                strategy=strategy,
                parameters=params,
                configuration=config,
                start=args.start,
                stop=args.stop,
                account=(AssetType(AssetType[args.account_asset]), args.account_balance, args.account_leverage),
                spread=(SpreadType(SpreadType[args.spread_type]), args.spread_value),
                commission=(CommissionType(CommissionType[args.commission_type]), args.commission_value),
                swap=(SwapType(SwapType[args.swap_type]), args.swap_buy, args.swap_sell),
                training=args.training,
                validation=args.validation,
                testing=args.testing,
                fitness=args.fitness,
                threads=args.threads
            )
        case SystemType.Learning.name:
            params: Parameters = parameters.Learning[args.strategy]
            system = LearningSystemAPI(
                broker=args.broker,
                group=args.group,
                symbol=args.symbol,
                timeframe=args.timeframe,
                strategy=strategy,
                parameters=params,
                start=args.start,
                stop=args.stop,
                balance=args.balance,
                spread=args.spread,
                episodes=args.episodes,
                fitness=args.fitness
            )

    if system is not None:
        with system:
            system.start()
            system.join()

if __name__ == "__main__":
    main()
