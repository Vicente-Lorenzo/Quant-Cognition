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
from Library.Utility.Typing import MISSING, Missing
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
    realtime_parser.add_argument("--universe-batch", type=int, required=False, default=MISSING)
    realtime_parser.add_argument("--universe-interval", type=float, required=False, default=MISSING)
    realtime_parser.add_argument("--universe-workers", type=int, required=False, default=MISSING)
    realtime_parser.add_argument("--universe-maxsize", type=int, required=False, default=MISSING)
    realtime_parser.add_argument("--market-batch", type=int, required=False, default=MISSING)
    realtime_parser.add_argument("--market-interval", type=float, required=False, default=MISSING)
    realtime_parser.add_argument("--market-workers", type=int, required=False, default=MISSING)
    realtime_parser.add_argument("--market-maxsize", type=int, required=False, default=MISSING)
    realtime_parser.add_argument("--portfolio-batch", type=int, required=False, default=MISSING)
    realtime_parser.add_argument("--portfolio-interval", type=float, required=False, default=MISSING)
    realtime_parser.add_argument("--portfolio-workers", type=int, required=False, default=MISSING)
    realtime_parser.add_argument("--portfolio-maxsize", type=int, required=False, default=MISSING)

    fee_parser = ArgumentParser(add_help=False)
    fee_parser.add_argument("--spread-type", type=str, required=False, default=SpreadType.Auto.name, choices=[_.name for _ in SpreadType])
    fee_parser.add_argument("--spread-value", type=float, required=False, default=MISSING)
    fee_parser.add_argument("--commission-type", type=str, required=False, default=CommissionType.Auto.name, choices=[_.name for _ in CommissionType])
    fee_parser.add_argument("--commission-value", type=float, required=False, default=MISSING)
    fee_parser.add_argument("--swap-type", type=str, required=False, default=SwapType.Auto.name, choices=[_.name for _ in SwapType])
    fee_parser.add_argument("--swap-buy", type=float, required=False, default=MISSING)
    fee_parser.add_argument("--swap-sell", type=float, required=False, default=MISSING)

    parser = ArgumentParser()
    system_parser = parser.add_subparsers(dest="system", required=True)

    system_parser.add_parser(SystemType.Live.name, parents=[base_parser, realtime_parser])
    system_parser.add_parser(SystemType.Simulation.name, parents=[base_parser, realtime_parser])
    system_parser.add_parser(SystemType.Testing.name, parents=[base_parser, realtime_parser])

    backtesting_parser = system_parser.add_parser(SystemType.Backtesting.name, parents=[base_parser, period_parser, account_parser, fee_parser])
    backtesting_parser.add_argument("--resolution", type=str, required=False, default=MISSING)

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

def _universe_(system: SystemType, batch: Union[int, Missing], interval: Union[float, Missing], workers: Union[int, Missing], maxsize: Union[int, Missing]) -> tuple[int, float, int, int]:
    match system:
        case SystemType.Live: auto_batch, auto_interval, auto_workers, auto_maxsize = 1, 0.0, 1, 64
        case SystemType.Simulation: auto_batch, auto_interval, auto_workers, auto_maxsize = 1, 0.0, 8, 64
        case _: auto_batch, auto_interval, auto_workers, auto_maxsize = 0, 0.0, 0, 0
    batch = batch if not isinstance(batch, Missing) else auto_batch
    interval = interval if not isinstance(interval, Missing) else auto_interval
    workers = workers if not isinstance(workers, Missing) else auto_workers
    maxsize = maxsize if not isinstance(maxsize, Missing) else auto_maxsize
    return batch, interval, workers, maxsize

def _market_(system: SystemType, strategy: StrategyType, batch: Union[int, Missing], interval: Union[float, Missing], workers: Union[int, Missing], maxsize: Union[int, Missing]) -> tuple[int, float, int, int]:
    download = strategy == StrategyType.Download
    match system:
        case SystemType.Live: auto_batch, auto_interval, auto_workers, auto_maxsize = 1000, 60.0, 1, 64
        case SystemType.Simulation: auto_batch, auto_interval, auto_workers, auto_maxsize = (100000, 0.0, 8, 8) if download else (50000, 0.0, 8, 64)
        case SystemType.Testing: auto_batch, auto_interval, auto_workers, auto_maxsize = (100000, 0.0, 8, 8) if download else (0, 0.0, 0, 0)
        case _: auto_batch, auto_interval, auto_workers, auto_maxsize = 0, 0.0, 0, 0
    batch = batch if not isinstance(batch, Missing) else auto_batch
    interval = interval if not isinstance(interval, Missing) else auto_interval
    workers = workers if not isinstance(workers, Missing) else auto_workers
    maxsize = maxsize if not isinstance(maxsize, Missing) else auto_maxsize
    return batch, interval, workers, maxsize

def _portfolio_(system: SystemType, batch: Union[int, Missing], interval: Union[float, Missing], workers: Union[int, Missing], maxsize: Union[int, Missing]) -> tuple[int, float, int, int]:
    match system:
        case SystemType.Live: auto_batch, auto_interval, auto_workers, auto_maxsize = 100, 60.0, 1, 64
        case SystemType.Simulation: auto_batch, auto_interval, auto_workers, auto_maxsize = 0, 0.0, 8, 64
        case _: auto_batch, auto_interval, auto_workers, auto_maxsize = 0, 0.0, 0, 0
    batch = batch if not isinstance(batch, Missing) else auto_batch
    interval = interval if not isinstance(interval, Missing) else auto_interval
    workers = workers if not isinstance(workers, Missing) else auto_workers
    maxsize = maxsize if not isinstance(maxsize, Missing) else auto_maxsize
    return batch, interval, workers, maxsize

def _strategy_(args: Namespace) -> Type[StrategyAPI]:
    match StrategyType(args.strategy):
        case StrategyType.Download: return DownloadStrategyAPI
        case StrategyType.NNFX: return NNFXStrategyAPI
        case StrategyType.DDPG: return DDPGStrategyAPI

def _system_(args: Namespace, strategy: Type[StrategyAPI], security: SecurityAPI, timeframe: TimeframeAPI, parameters: Parameter) -> Union[SystemAPI, None]:
    system = SystemType(args.system)
    strategy_type = StrategyType(args.strategy)
    match system:
        case SystemType.Live | SystemType.Simulation | SystemType.Testing:
            params: Parameter = parameters.Realtime[args.strategy]
            return RealtimeAPI(
                system=system,
                strategy=strategy,
                security=security,
                timeframe=timeframe,
                parameters=params,
                iid=args.iid,
                database=args.database,
                universe=_universe_(system, args.universe_batch, args.universe_interval, args.universe_workers, args.universe_maxsize),
                market=_market_(system, strategy_type, args.market_batch, args.market_interval, args.market_workers, args.market_maxsize),
                portfolio=_portfolio_(system, args.portfolio_batch, args.portfolio_interval, args.portfolio_workers, args.portfolio_maxsize),
                report=args.report,
                export=args.export
            )
        case SystemType.Backtesting:
            params: Parameter = parameters.Backtesting[args.strategy]
            return BacktestingAPI(
                strategy=strategy,
                security=security,
                timeframe=timeframe,
                resolution=args.resolution,
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
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"): stream.reconfigure(encoding="utf-8", errors="replace")
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
            provider_uid, ticker_uid = ProviderAPI.normalize(args.provider), TickerAPI.normalize(args.ticker)
            ticker = TickerAPI(UID=ticker_uid, db=db, autoload=True)
            provider = ProviderAPI(UID=provider_uid, db=db, autoload=True)
            timeframe = TimeframeAPI(UID=TimeframeAPI.normalize(args.timeframe), db=db, autoload=True)
            security = SecurityAPI(Provider=provider, Ticker=ticker, db=db, autoload=True)
            category = security.Category
            if category is None: raise ValueError(f"Security {provider_uid} {ticker_uid}: Failed · Due to missing Category")
            parameters = parameterise[provider.UID][category.UID][ticker.UID][args.timeframe]
            strategy = _strategy_(args)
            system = _system_(args, strategy, security, timeframe, parameters)
            if system is None: return
            with system:
                system.run()
    if args.profile: profiler(run)()
    else: run()

if __name__ == "__main__":
    main()