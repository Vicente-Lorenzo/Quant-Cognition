import os
from typing import Type, Union
from argparse import ArgumentParser, Namespace

from Library.Utility.Statistic import timer
from Library.System.System import SystemType
from Library.Strategy.Model import DDPGStrategyAPI
from Library.Strategy.Strategy import StrategyType
from Library.System import RealtimeSystemAPI, SystemAPI
from Library.Parameters import Parameters, ParametersAPI
from Library.Utility.Path import traceback_current_module
from Library.Logging import HandlerLoggingAPI, VerboseLevel
from Library.Database.Postgres.Postgres import PostgresDatabaseAPI
from Library.Strategy import DownloadStrategyAPI, NNFXStrategyAPI, StrategyAPI
from Library.Universe import CommissionType, Provider, ProviderAPI, SecurityAPI, SpreadType, SwapType, TickerAPI, TimeframeAPI

def _parse_() -> Namespace:
    base_parser = ArgumentParser(add_help=False)
    base_parser.add_argument("--console", type=str, required=True, choices=[_.name for _ in VerboseLevel])
    base_parser.add_argument("--file", type=str, required=True, choices=[_.name for _ in VerboseLevel])
    base_parser.add_argument("--strategy", type=str, required=True, choices=[_.name for _ in StrategyType])
    base_parser.add_argument("--provider", type=str, required=True, choices=[_.name for _ in Provider])
    base_parser.add_argument("--ticker", type=str, required=True)
    base_parser.add_argument("--timeframe", type=str, required=True)

    period_parser = ArgumentParser(add_help=False)
    period_parser.add_argument("--start", type=str, required=True)
    period_parser.add_argument("--stop", type=str, required=True)

    account_parser = ArgumentParser(add_help=False)
    account_parser.add_argument("--account-asset", type=str, required=True)
    account_parser.add_argument("--account-balance", type=float, required=True)
    account_parser.add_argument("--account-leverage", type=float, required=True)

    realtime_parser = ArgumentParser(add_help=False)
    realtime_parser.add_argument("--iid", type=str, required=True)

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

def _strategy_(args: Namespace) -> Union[Type[StrategyAPI], None]:
    match StrategyType(args.strategy):
        case StrategyType.Download: return DownloadStrategyAPI
        case StrategyType.NNFX: return NNFXStrategyAPI
        case StrategyType.DDPG: return DDPGStrategyAPI

def _system_(args: Namespace, strategy: Type[StrategyAPI], security: SecurityAPI, timeframe: TimeframeAPI, parameters: Parameters) -> Union[SystemAPI, None]:
    match SystemType(args.system):
        case SystemType.Live:
            params: Parameters = parameters.Live[args.strategy]
            return RealtimeSystemAPI(
                strategy=strategy,
                security=security,
                timeframe=timeframe,
                parameters=params,
                iid=args.iid,
                batch=100,
                interval=60.0
            )
        case SystemType.Simulation:
            params: Parameters = parameters.Simulation[args.strategy]
            return RealtimeSystemAPI(
                strategy=strategy,
                security=security,
                timeframe=timeframe,
                parameters=params,
                iid=args.iid,
                batch=5000,
                interval=0.0
            )
        case SystemType.Testing:
            params: Parameters = parameters.Testing[args.strategy]
            return RealtimeSystemAPI(
                strategy=strategy,
                security=security,
                timeframe=timeframe,
                parameters=params,
                iid=args.iid,
                batch=0,
                interval=0.0
            )
        case SystemType.Backtesting:
            return None
        #     params: Parameters = parameters.Backtesting[args.strategy]
        #     return BacktestingSystemAPI(
        #         strategy=strategy,
        #         security=security,
        #         timeframe=timeframe,
        #         parameters=params,
        #         start=args.start,
        #         stop=args.stop,
        #         account=(args.account_asset, args.account_balance, args.account_leverage),
        #         spread=(SpreadType(args.spread_type), args.spread_value),
        #         commission=(CommissionType(args.commission_type), args.commission_value),
        #         swap=(SwapType(args.swap_type), args.swap_buy, args.swap_sell)
        #     )
        case SystemType.Optimization:
            return None
        #     params: Parameters = parameters.Backtesting[args.strategy]
        #     config: Parameters = parameters.Optimization[args.strategy]
        #     return OptimizationSystemAPI(
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
        #     params: Parameters = parameters.Learning[args.strategy]
        #     return LearningSystemAPI(
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
    parameterise: ParametersAPI = ParametersAPI()
    execution: str = traceback_current_module().name

    log: HandlerLoggingAPI = HandlerLoggingAPI(Class=execution, Subclass="Execution Management")
    log.console.set_verbose_level(VerboseLevel[args.console])
    log.file.set_verbose_level(VerboseLevel[args.file])

    @timer
    @log.guard
    def run() -> None:
        db = PostgresDatabaseAPI(database="Quant")
        db.connect()
        ticker = TickerAPI(UID=TickerAPI.normalize(args.ticker), db=db, autoload=True)
        provider = ProviderAPI(UID=ProviderAPI.normalize(args.provider), db=db, autoload=True)
        timeframe = TimeframeAPI(UID=TimeframeAPI.normalize(args.timeframe), db=db, autoload=True)
        security = SecurityAPI(Provider=provider, Ticker=ticker, db=db, autoload=True)
        parameters: Parameters = parameterise[provider.UID][security.Category.UID][ticker.UID][timeframe.UID]
        strategy = _strategy_(args)
        system = _system_(args, strategy, security, timeframe, parameters)
        with system:
            system.run()
        db.disconnect()

    run()

if __name__ == "__main__":
    main()
