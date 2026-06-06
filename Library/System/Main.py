import os
import sys
from pathlib import Path
from typing import Type, Union
from argparse import ArgumentParser, Namespace

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from Library.Utility.Statistic import profiler, timer
from Library.System.System import SystemType
from Library.Strategy.Model import DDPGStrategyAPI
from Library.Strategy.Strategy import StrategyType
from Library.System import BacktestingAPI, RealtimeAPI, SystemAPI
from Library.Parameter import Parameter, ParameterAPI
from Library.Utility.Path import traceback_current_module
from Library.Logging import HandlerLoggingAPI, VerboseLevel
from Library.Database.Postgres.Postgres import PostgresAPI
from Library.Strategy import DownloadStrategyAPI, NNFXStrategyAPI, StrategyAPI
from Library.Universe import CommissionType, ProviderAPI, SecurityAPI, SpreadType, SwapType, TickerAPI, TimeframeAPI

def _parse_() -> Namespace:
    base_parser = ArgumentParser(add_help=False)
    base_parser.add_argument("--console", type=str, required=True, choices=[_.name for _ in VerboseLevel])
    base_parser.add_argument("--file", type=str, required=True, choices=[_.name for _ in VerboseLevel])
    base_parser.add_argument("--strategy", type=str, required=True, choices=[_.name for _ in StrategyType])
    base_parser.add_argument("--provider", type=str, required=True)
    base_parser.add_argument("--ticker", type=str, required=True)
    base_parser.add_argument("--timeframe", type=str, required=True)
    base_parser.add_argument("--report", action="store_true", default=False)
    base_parser.add_argument("--export", action="store_true", default=False)
    base_parser.add_argument("--profile", action="store_true", default=False)

    period_parser = ArgumentParser(add_help=False)
    period_parser.add_argument("--start", type=str, required=True)
    period_parser.add_argument("--stop", type=str, required=True)

    account_parser = ArgumentParser(add_help=False)
    account_parser.add_argument("--account-asset", type=str, required=True)
    account_parser.add_argument("--account-balance", type=float, required=True)
    account_parser.add_argument("--account-leverage", type=float, required=True)

    realtime_parser = ArgumentParser(add_help=False)
    realtime_parser.add_argument("--iid", type=str, required=True)
    realtime_parser.add_argument("--database", type=str, required=False, default=None, choices=["Quant", "Tests"])
    realtime_parser.add_argument("--universe-batch", type=int, required=False, default=None)
    realtime_parser.add_argument("--universe-interval", type=float, required=False, default=None)
    realtime_parser.add_argument("--market-batch", type=int, required=False, default=None)
    realtime_parser.add_argument("--market-interval", type=float, required=False, default=None)
    realtime_parser.add_argument("--portfolio-batch", type=int, required=False, default=None)
    realtime_parser.add_argument("--portfolio-interval", type=float, required=False, default=None)

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

    system_parser.add_parser(SystemType.Live.name, parents=[base_parser, realtime_parser])
    system_parser.add_parser(SystemType.Simulation.name, parents=[base_parser, realtime_parser])
    system_parser.add_parser(SystemType.Testing.name, parents=[base_parser, realtime_parser])

    system_parser.add_parser(SystemType.Backtesting.name, parents=[base_parser, period_parser, account_parser, fee_parser])

    optimization_parser = system_parser.add_parser(SystemType.Optimization.name, parents=[base_parser, period_parser, account_parser, fee_parser])
    optimization_parser.add_argument("--training", type=int, required=True)
    optimization_parser.add_argument("--validation", type=int, required=True)
    optimization_parser.add_argument("--testing", type=int, required=True)
    optimization_parser.add_argument("--fitness", type=str, required=True)
    optimization_parser.add_argument("--threads", type=int, required=False, default=os.cpu_count())

    learning_parser = system_parser.add_parser(SystemType.Learning.name, parents=[base_parser, period_parser, account_parser, fee_parser])
    learning_parser.add_argument("--reward", type=str, required=True)
    learning_parser.add_argument("--episodes", type=int, required=True)

    return parser.parse_args()

def _universe_(system: SystemType, batch: Union[int, None], interval: Union[float, None]) -> tuple[int, float]:
    match system:
        case SystemType.Live | SystemType.Simulation: auto_batch, auto_interval = 1, 0.0
        case _: auto_batch, auto_interval = 0, 0.0
    batch = batch if batch is not None else auto_batch
    interval = interval if interval is not None else auto_interval
    return batch, interval

def _market_(system: SystemType, batch: Union[int, None], interval: Union[float, None]) -> tuple[int, float]:
    match system:
        case SystemType.Live: auto_batch, auto_interval = 100, 60.0
        case SystemType.Simulation: auto_batch, auto_interval = 5000, 0.0
        case _: auto_batch, auto_interval = 0, 0.0
    batch = batch if batch is not None else auto_batch
    interval = interval if interval is not None else auto_interval
    return batch, interval

def _portfolio_(system: SystemType, batch: Union[int, None], interval: Union[float, None]) -> tuple[int, float]:
    match system:
        case SystemType.Live: auto_batch, auto_interval = 100, 60.0
        case _: auto_batch, auto_interval = 0, 0.0
    batch = batch if batch is not None else auto_batch
    interval = interval if interval is not None else auto_interval
    return batch, interval

def _strategy_(args: Namespace) -> Union[Type[StrategyAPI], None]:
    match StrategyType(args.strategy):
        case StrategyType.Download: return DownloadStrategyAPI
        case StrategyType.NNFX: return NNFXStrategyAPI
        case StrategyType.DDPG: return DDPGStrategyAPI

def _system_(args: Namespace, strategy: Type[StrategyAPI], security: SecurityAPI, timeframe: TimeframeAPI, parameters: Parameter) -> Union[SystemAPI, None]:
    match SystemType(args.system):
        case SystemType.Live:
            params: Parameter = parameters.Realtime[args.strategy]
            return RealtimeAPI(
                system=SystemType.Live,
                strategy=strategy,
                security=security,
                timeframe=timeframe,
                parameters=params,
                iid=args.iid,
                database=args.database,
                universe=_universe_(SystemType(args.system), args.universe_batch, args.universe_interval),
                market=_market_(SystemType(args.system), args.market_batch, args.market_interval),
                portfolio=_portfolio_(SystemType(args.system), args.portfolio_batch, args.portfolio_interval),
                report=args.report,
                export=args.export
            )
        case SystemType.Simulation:
            params: Parameter = parameters.Realtime[args.strategy]
            return RealtimeAPI(
                system=SystemType.Simulation,
                strategy=strategy,
                security=security,
                timeframe=timeframe,
                parameters=params,
                iid=args.iid,
                database=args.database,
                universe=_universe_(SystemType(args.system), args.universe_batch, args.universe_interval),
                market=_market_(SystemType(args.system), args.market_batch, args.market_interval),
                portfolio=_portfolio_(SystemType(args.system), args.portfolio_batch, args.portfolio_interval),
                report=args.report,
                export=args.export
            )
        case SystemType.Testing:
            params: Parameter = parameters.Realtime[args.strategy]
            return RealtimeAPI(
                system=SystemType.Testing,
                strategy=strategy,
                security=security,
                timeframe=timeframe,
                parameters=params,
                iid=args.iid,
                database=args.database,
                universe=_universe_(SystemType(args.system), args.universe_batch, args.universe_interval),
                market=_market_(SystemType(args.system), args.market_batch, args.market_interval),
                portfolio=_portfolio_(SystemType(args.system), args.portfolio_batch, args.portfolio_interval),
                report=args.report,
                export=args.export
            )
        case SystemType.Backtesting:
            params: Parameter = parameters.Backtesting[args.strategy]
            return BacktestingAPI(
                strategy=strategy,
                security=security,
                timeframe=timeframe,
                parameters=params,
                start=args.start,
                stop=args.stop,
                account=(args.account_asset, args.account_balance, args.account_leverage),
                spread=(SpreadType(args.spread_type), args.spread_value),
                commission=(CommissionType(args.commission_type), args.commission_value),
                swap=(SwapType(args.swap_type), args.swap_buy, args.swap_sell),
                report=args.report,
                export=args.export
            )
        case SystemType.Optimization:
            return None
        #     params: Parameter = parameters.Backtesting[args.strategy]
        #     config: Parameter = parameters.Optimization[args.strategy]
        #     return OptimizationAPI(
        #         strategy=strategy,
        #         security=security,
        #         timeframe=timeframe,
        #         parameters=params,
        #         configuration=config,
        #         start=args.start,
        #         stop=args.stop,
        #         account=(args.account_asset, args.account_balance, args.account_leverage),
        #         spread=(SpreadType(args.spread_type), args.spread_value),
        #         commission=(CommissionType(args.commission_type), args.commission_value),
        #         swap=(SwapType(args.swap_type), args.swap_buy, args.swap_sell),
        #         training=args.training,
        #         validation=args.validation,
        #         testing=args.testing,
        #         fitness=args.fitness,
        #         threads=args.threads
        #     )
        case SystemType.Learning:
            return None
        #     params: Parameter = parameters.Learning[args.strategy]
        #     return LearningAPI(
        #         strategy=strategy,
        #         security=security,
        #         timeframe=timeframe,
        #         parameters=params,
        #         start=args.start,
        #         stop=args.stop,
        #         account=(args.account_asset, args.account_balance, args.account_leverage),
        #         spread=(SpreadType(args.spread_type), args.spread_value),
        #         commission=(CommissionType(args.commission_type), args.commission_value),
        #         swap=(SwapType(args.swap_type), args.swap_buy, args.swap_sell),
        #         reward=args.reward,
        #         episodes=args.episodes
        #     )

def main() -> None:
    args: Namespace = _parse_()
    parameterise: ParameterAPI = ParameterAPI()
    execution: str = traceback_current_module().name

    log: HandlerLoggingAPI = HandlerLoggingAPI(Class=execution, Subclass="Execution Management")
    log.set_class_tags(args.provider, args.ticker, args.timeframe)
    log.console.set_verbose_level(VerboseLevel[args.console])
    log.file.set_verbose_level(VerboseLevel[args.file])

    @timer
    @log.guard
    def run() -> None:
        with PostgresAPI(database="Quant") as db:
            ticker = TickerAPI(UID=TickerAPI.normalize(args.ticker), db=db, autoload=True)
            provider = ProviderAPI(UID=ProviderAPI.normalize(args.provider), db=db, autoload=True)
            timeframe = TimeframeAPI(UID=TimeframeAPI.normalize(args.timeframe), db=db, autoload=True)
            security = SecurityAPI(Provider=provider, Ticker=ticker, db=db, autoload=True)
            parameters: Parameter = parameterise[provider.UID][security.Category.UID][ticker.UID][args.timeframe]
            strategy = _strategy_(args)
            system = _system_(args, strategy, security, timeframe, parameters)
            with system:
                system.run()
    if args.profile: profiler(run)()
    else: run()

if __name__ == "__main__":
    main()