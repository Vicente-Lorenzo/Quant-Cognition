import sys
import json
import yaml
import uuid
from argparse import ArgumentParser, Namespace
from datetime import datetime
from functools import partial
from pathlib import Path
from typing import Union

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from Library.Database.Postgres.Postgres import PostgresDatabaseAPI
from Library.Logging import LoggingAPI, VerboseLevel
from Library.Strategy import DDPGStrategyAPI, DownloadStrategyAPI, LadderAPI, NNFXStrategyAPI, RewardType, StrategyAPI, StrategyType, TrendStrategyAPI
from Library.System import BacktestingAPI, ElectionMode, FitnessType, LearningAPI, OptimizationAPI, RealtimeAPI, SelectionMode, SystemAPI, SystemType
from Library.Universe import CommissionType, ProviderAPI, SecurityAPI, SpreadType, SwapType, TickerAPI, TimeframeAPI
from Library.Utility import HORIZON, MISSING, Missing, Parameter, inspect_temporary, profiler, timer

def _parse_() -> Namespace:
    base_parser = ArgumentParser(add_help=False)
    base_parser.add_argument("--console", type=str, default=VerboseLevel.Debug.name, choices=[_.name for _ in VerboseLevel])
    base_parser.add_argument("--file", type=str, default=VerboseLevel.Debug.name, choices=[_.name for _ in VerboseLevel])
    base_parser.add_argument("--storage", type=str, default=VerboseLevel.Warning.name, choices=[_.name for _ in VerboseLevel])
    base_parser.add_argument("--strategy", type=str, default=StrategyType.Download.name, choices=[_.name for _ in StrategyType])
    base_parser.add_argument("--provider", type=str, default="Spotware")
    base_parser.add_argument("--ticker", type=str, default="EURUSD")
    base_parser.add_argument("--timeframe", type=str, default="Daily")
    base_parser.add_argument("--risk-free", type=float, default=0.0)
    base_parser.add_argument("--benchmark", type=str, nargs="?", const="", default=None)
    base_parser.add_argument("--report", action="store_true", default=False)
    base_parser.add_argument("--export", nargs="?", const=True, default=False, metavar="PATH")
    base_parser.add_argument("--plot", nargs="?", const=True, default=False, metavar="PATH")
    base_parser.add_argument("--description", type=str, default=None)
    base_parser.add_argument("--profile", nargs="?", const=True, default=False, metavar="PATH")
    base_parser.add_argument("--run", type=str, default=None, metavar="FOLDER")

    period_parser = ArgumentParser(add_help=False)
    period_parser.add_argument("--start", type=str, default=HORIZON.strftime("%Y-%m-%d"))
    period_parser.add_argument("--stop", type=str, default="2030-01-01")

    account_parser = ArgumentParser(add_help=False)
    account_parser.add_argument("--account-asset", type=str, default="EUR")
    account_parser.add_argument("--account-balance", type=float, default=10000.0)
    account_parser.add_argument("--account-leverage", type=float, default=30.0)

    realtime_parser = ArgumentParser(add_help=False)
    realtime_parser.add_argument("--iid", type=str, default=None)
    realtime_parser.add_argument("--database", type=str, default=None, choices=["Quant", "Tests"])
    realtime_parser.add_argument("--universe-batch", type=int, default=MISSING)
    realtime_parser.add_argument("--universe-interval", type=float, default=MISSING)
    realtime_parser.add_argument("--universe-workers", type=int, default=MISSING)
    realtime_parser.add_argument("--universe-maxsize", type=int, default=MISSING)
    realtime_parser.add_argument("--market-batch", type=int, default=MISSING)
    realtime_parser.add_argument("--market-interval", type=float, default=MISSING)
    realtime_parser.add_argument("--market-workers", type=int, default=MISSING)
    realtime_parser.add_argument("--market-maxsize", type=int, default=MISSING)
    realtime_parser.add_argument("--portfolio-batch", type=int, default=MISSING)
    realtime_parser.add_argument("--portfolio-interval", type=float, default=MISSING)
    realtime_parser.add_argument("--portfolio-workers", type=int, default=MISSING)
    realtime_parser.add_argument("--portfolio-maxsize", type=int, default=MISSING)

    fee_parser = ArgumentParser(add_help=False)
    fee_parser.add_argument("--spread-type", type=str, default=SpreadType.Auto.name, choices=[_.name for _ in SpreadType])
    fee_parser.add_argument("--spread-value", type=float, default=MISSING)
    fee_parser.add_argument("--commission-type", type=str, default=CommissionType.Auto.name, choices=[_.name for _ in CommissionType])
    fee_parser.add_argument("--commission-value", type=float, default=MISSING)
    fee_parser.add_argument("--swap-type", type=str, default=SwapType.Auto.name, choices=[_.name for _ in SwapType])
    fee_parser.add_argument("--swap-buy", type=float, default=MISSING)
    fee_parser.add_argument("--swap-sell", type=float, default=MISSING)

    parser = ArgumentParser()
    system_parser = parser.add_subparsers(dest="system", required=True)

    system_parser.add_parser(SystemType.Live.name, parents=[base_parser, realtime_parser])
    system_parser.add_parser(SystemType.Simulation.name, parents=[base_parser, realtime_parser])
    system_parser.add_parser(SystemType.Testing.name, parents=[base_parser, realtime_parser])

    backtesting_parser = system_parser.add_parser(SystemType.Backtesting.name, parents=[base_parser, period_parser, account_parser, fee_parser])
    backtesting_parser.add_argument("--resolution", type=str, default=MISSING)

    optimization_parser = system_parser.add_parser(SystemType.Optimization.name, parents=[base_parser, period_parser, account_parser, fee_parser])
    optimization_parser.add_argument("--training", type=int, default=0)
    optimization_parser.add_argument("--validation", type=int, default=0)
    optimization_parser.add_argument("--testing", type=int, default=0)
    optimization_parser.add_argument("--fitness", type=str, default=FitnessType.AnnualizedReturn.name, choices=[_.name for _ in FitnessType])
    optimization_parser.add_argument("--resolution", type=str, default=MISSING)
    optimization_parser.add_argument("--selection", type=str, default=SelectionMode.Best.name, choices=[_.name for _ in SelectionMode])
    optimization_parser.add_argument("--election", type=str, default=ElectionMode.Frequency.name, choices=[_.name for _ in ElectionMode])
    optimization_parser.add_argument("--purge", type=int, default=None)
    optimization_parser.add_argument("--embargo", type=int, default=None)
    optimization_parser.add_argument("--rolling", action="store_true")
    optimization_parser.add_argument("--continuous", action="store_true", default=False)
    optimization_parser.add_argument("--workers", type=int, default=1)

    learning_parser = system_parser.add_parser(SystemType.Learning.name, parents=[base_parser, period_parser, account_parser, fee_parser])
    learning_parser.add_argument("--selection", type=str, default=SelectionMode.Best.name, choices=[_.name for _ in SelectionMode])
    learning_parser.add_argument("--election", type=str, default=ElectionMode.Last.name, choices=[_.name for _ in ElectionMode])
    learning_parser.add_argument("--purge", type=int, default=None)
    learning_parser.add_argument("--embargo", type=int, default=None)
    learning_parser.add_argument("--reward", type=str, default=RewardType.LogReturn.name, choices=[_.name for _ in RewardType])
    learning_parser.add_argument("--episodes", type=int, default=1)
    learning_parser.add_argument("--epochs", type=int, default=1)
    learning_parser.add_argument("--train-frequency", type=int, default=1)
    learning_parser.add_argument("--gradient-steps", type=int, default=1)
    learning_parser.add_argument("--training", type=int, default=0)
    learning_parser.add_argument("--validation", type=int, default=0)
    learning_parser.add_argument("--testing", type=int, default=0)
    learning_parser.add_argument("--rolling", action="store_true", default=False)
    learning_parser.add_argument("--continuous", action="store_true", default=False)
    learning_parser.add_argument("--fitness", type=str, default=FitnessType.AnnualizedReturn.name, choices=[_.name for _ in FitnessType])
    learning_parser.add_argument("--patience", type=int, default=0)
    learning_parser.add_argument("--activity", type=int, default=0)
    learning_parser.add_argument("--balance", type=int, default=0)
    learning_parser.add_argument("--ratio", type=float, default=0.0)
    learning_parser.add_argument("--mirror", action="store_true", default=False)
    learning_parser.add_argument("--mirror-ratio", type=float, default=0.5)
    learning_parser.add_argument("--final", action="store_true", default=False)
    learning_parser.add_argument("--seed", type=int, default=None)
    learning_parser.add_argument("--seeds", type=int, default=1)
    learning_parser.add_argument("--workers", type=int, default=1)
    learning_parser.add_argument("--threads", type=int, default=None)

    return parser.parse_args()

def _settled_(given: tuple, automatic: tuple) -> tuple:
    return tuple(fallback if isinstance(value, Missing) else value for value, fallback in zip(given, automatic))

def _universe_(system: SystemType, batch: Union[int, Missing], interval: Union[float, Missing], workers: Union[int, Missing], maxsize: Union[int, Missing]) -> tuple[int, float, int, int]:
    match system:
        case SystemType.Live: automatic = 1, 0.0, 1, 64
        case SystemType.Simulation: automatic = 1, 0.0, 8, 64
        case _: automatic = 0, 0.0, 0, 0
    return _settled_((batch, interval, workers, maxsize), automatic)

def _market_(system: SystemType, strategy: StrategyType, batch: Union[int, Missing], interval: Union[float, Missing], workers: Union[int, Missing], maxsize: Union[int, Missing]) -> tuple[int, float, int, int]:
    download = strategy == StrategyType.Download
    match system:
        case SystemType.Live: automatic = 1000, 60.0, 1, 64
        case SystemType.Simulation: automatic = (500000, 0.0, 8, 16) if download else (0, 0.0, 0, 0)
        case SystemType.Testing: automatic = (500000, 0.0, 8, 16) if download else (0, 0.0, 0, 0)
        case _: automatic = 0, 0.0, 0, 0
    return _settled_((batch, interval, workers, maxsize), automatic)

def _portfolio_(system: SystemType, batch: Union[int, Missing], interval: Union[float, Missing], workers: Union[int, Missing], maxsize: Union[int, Missing]) -> tuple[int, float, int, int]:
    match system:
        case SystemType.Live: automatic = 100, 60.0, 1, 64
        case SystemType.Simulation: automatic = 0, 0.0, 8, 64
        case _: automatic = 0, 0.0, 0, 0
    return _settled_((batch, interval, workers, maxsize), automatic)

def _strategy_(args: Namespace) -> type[StrategyAPI]:
    match StrategyType(args.strategy):
        case StrategyType.Download: return DownloadStrategyAPI
        case StrategyType.NNFX: return NNFXStrategyAPI
        case StrategyType.DDPG: return DDPGStrategyAPI
        case StrategyType.Trend: return TrendStrategyAPI

def _system_(args: Namespace, strategy: type[StrategyAPI], security: SecurityAPI, timeframe: TimeframeAPI, resolve) -> Union[SystemAPI, None]:
    system = SystemType(args.system)
    strategy_type = StrategyType(args.strategy)
    match system:
        case SystemType.Live | SystemType.Simulation | SystemType.Testing:
            params: Parameter = resolve("Realtime")
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
                risk_free=args.risk_free,
                benchmark=args.benchmark,
                report=args.report,
                export=args.export,
                plot=args.plot,
                run=args.run,
                description=args.description
            )
        case SystemType.Backtesting:
            params: Parameter = resolve("Backtesting")
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
                risk_free=args.risk_free,
                benchmark=args.benchmark,
                report=args.report,
                export=args.export,
                plot=args.plot,
                run=args.run,
                description=args.description
            )
        case SystemType.Optimization:
            params: Parameter = resolve("Backtesting")
            space: Parameter = resolve("Optimization")
            return OptimizationAPI(
                strategy=strategy,
                security=security,
                timeframe=timeframe,
                resolution=args.resolution,
                parameters=params,
                space=space,
                start=args.start,
                stop=args.stop,
                account=(args.account_asset, args.account_balance, args.account_leverage),
                spread=(SpreadType(args.spread_type), args.spread_value),
                commission=(CommissionType(args.commission_type), args.commission_value),
                swap=(SwapType(args.swap_type), args.swap_buy, args.swap_sell),
                fitness=args.fitness,
                selection=args.selection,
                election=args.election,
                purge=args.purge,
                embargo=args.embargo,
                training=args.training,
                validation=args.validation,
                testing=args.testing,
                rolling=args.rolling,
                continuous=args.continuous,
                workers=args.workers,
                risk_free=args.risk_free,
                report=args.report,
                export=args.export,
                plot=args.plot,
                run=args.run,
                description=args.description
            )
        case SystemType.Learning:
            params: Parameter = resolve("Learning")
            return LearningAPI(
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
                reward=args.reward,
                episodes=args.episodes,
                epochs=args.epochs,
                train_frequency=args.train_frequency,
                gradient_steps=args.gradient_steps,
                training=args.training,
                validation=args.validation,
                testing=args.testing,
                rolling=args.rolling,
                continuous=args.continuous,
                fitness=args.fitness,
                selection=args.selection,
                election=args.election,
                purge=args.purge,
                embargo=args.embargo,
                patience=args.patience,
                activity=args.activity,
                balance=args.balance,
                ratio=args.ratio,
                mirror=args.mirror,
                mirror_ratio=args.mirror_ratio,
                final=args.final,
                seed=args.seed,
                seeds=args.seeds,
                workers=args.workers,
                threads=args.threads,
                benchmark=args.benchmark,
                report=args.report,
                export=args.export,
                plot=args.plot,
                run=args.run,
                description=args.description
            )

def _parameters_(ladder: LadderAPI, strategy: type[StrategyAPI], rungs: tuple, trails: dict, kind: str) -> Parameter:
    parameters, trails[kind] = ladder.parameterize(strategy, kind, *rungs)
    return parameters

def _scope_(provider, category, ticker, timeframe) -> tuple:
    return (provider.UID, category.UID, ticker.UID, TimeframeAPI.normalize(timeframe.UID))

def _snapshot_(folder: Path, args: Namespace, parameters, log: LoggingAPI, trails: Union[dict, None] = None, rungs: tuple = ()) -> None:
    try:
        entry = folder / "Input"
        entry.mkdir(parents=True, exist_ok=True)
        data = getattr(parameters, "data", None)
        if data is not None: (entry / "Parameters.yml").write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
        manifest = {"System": args.system, "Strategy": args.strategy, "Provider": args.provider, "Ticker": args.ticker,
                    "Timeframe": args.timeframe, "Start": str(args.start), "Stop": str(args.stop),
                    "Description": args.description, "StartedAt": datetime.now().isoformat(),
                    "Command": " ".join(sys.argv[1:]),
                    "Parameters": trails or None,
                    "Scope": list(rungs) or None}
        (folder / "Run.json").write_text(json.dumps({key: value for key, value in manifest.items() if value is not None}, indent=2), encoding="utf-8")
    except Exception as error:
        log.warning(lambda error=error: f"Snapshot Operation: Failed · {error}")

def main() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"): stream.reconfigure(encoding="utf-8", errors="replace")
    args: Namespace = _parse_()
    ladder: LadderAPI = LadderAPI()

    log: LoggingAPI = LoggingAPI("Execution Management")
    log.set_shared_tags(args.provider, args.ticker, args.timeframe)
    log.console.set_level(VerboseLevel[args.console])
    log.file.set_level(VerboseLevel[args.file])
    log.storage.set_level(VerboseLevel[args.storage])
    folder = Path(args.run) if args.run else inspect_temporary("Runs", uuid.uuid4().hex)
    folder.mkdir(parents=True, exist_ok=True)
    args.run = str(folder)
    log.file.set_path(folder)
    log.file.set_name("Run")
    if args.profile is True: args.profile = str(folder / "Output")

    @timer
    @log.guard
    def run() -> None:
        with PostgresDatabaseAPI(database="Quant") as db:
            provider_uid, ticker_uid = ProviderAPI.normalize(args.provider), TickerAPI.normalize(args.ticker)
            ticker = TickerAPI(UID=ticker_uid, db=db, autoload=True)
            provider = ProviderAPI(UID=provider_uid, db=db, autoload=True)
            timeframe = TimeframeAPI(UID=TimeframeAPI.normalize(args.timeframe), db=db, autoload=True)
            security = SecurityAPI(Provider=provider, Ticker=ticker, db=db, autoload=True)
            category = security.Category
            if category is None: raise ValueError(f"Security {provider_uid} {ticker_uid}: Failed · Due to missing Category")
            strategy = _strategy_(args)
            rungs = _scope_(provider, category, ticker, timeframe)
            trails = {}
            resolve = partial(_parameters_, ladder, strategy, rungs, trails)
            system = _system_(args, strategy, security, timeframe, resolve)
            if system is None: return
            _snapshot_(folder, args, getattr(system, "_parameters_", None), log, trails, rungs)
            with system:
                system.run()
    if args.profile: profiler(run, args.profile)()
    else: run()

if __name__ == "__main__":
    main()