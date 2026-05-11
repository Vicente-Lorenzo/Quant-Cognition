import copy
import itertools
import threading

import numpy as np

from tqdm import tqdm
from typing import Union, Type, Callable
from concurrent.futures import as_completed, ThreadPoolExecutor

from datetime import date
from dateutil.relativedelta import relativedelta

from Library.Database.Dataframe import pl
from Library.Classes import *
from Library.Parameters import Parameters
from Library.Utils import timer, image, gantt

from Library.Market import MarketAPI, MARGIN
from Library.Portfolio import StatisticsAPI
from Library.Strategy import StrategyAPI
from Library.System import BacktestingSystemAPI

class OptimizationSystemAPI(BacktestingSystemAPI):

    WFSTAGEID = "Walk-Forward ID"
    WFOPTSTART = "Optimization Start"
    WFOPTSTOP = "Optimization Stop"
    WFVALSTART = "Validation Start"
    WFVALSTOP = "Validation Stop"
    WFOPTFITNESS = "{0} (Optimization)"
    WFVALFITNESS = "{0} (Validation)"

    DOFSTAGEID = "Degrees-of-Freedom ID"
    CTFSTAGEID = "Coarse-to-Fine ID"
    BACKTESTSTAGEID = "Backtest ID"

    def __init__(self,
                 broker: str,
                 group: str,
                 symbol: str,
                 timeframe: str,
                 strategy: Type[StrategyAPI],
                 parameters: Parameters,
                 configuration: Parameters,
                 start: Union[str, date],
                 stop: Union[str, date],
                 account: tuple[AssetType, float, float],
                 spread: tuple[SpreadType, float],
                 commission: tuple[CommissionType, float],
                 swap: tuple[SwapType, float, float],
                 training: int,
                 validation: int,
                 testing: int,
                 fitness: str,
                 threads: Union[int, None]) -> None:

        super().__init__(
            broker=broker,
            group=group,
            symbol=symbol,
            timeframe=timeframe,
            strategy=strategy,
            parameters=parameters,
            start=start,
            stop=stop,
            account=account,
            spread=spread,
            commission=commission,
            swap=swap
        )

        self._configuration: Parameters = configuration
        self._training: int = training
        self._validation: int = validation
        self._testing: int = testing
        self._fitness: str = fitness

        self._wf_stages = self.unpack_walk_forward_stages(self._start_date, self._stop_date, self._training, self._validation, self._testing)

        self._dof_stages = self.unpack_degrees_of_freedom_stages(self._configuration.MoneyManagement,
                                                                 self._configuration.RiskManagement,
                                                                 self._configuration.SignalManagement,
                                                                 self._configuration.AnalystManagement,
                                                                 self._configuration.ManagerManagement)

        self.window: int = self.unpack_degrees_of_freedom_window(self._dof_stages)

        self._btid_lock = threading.Lock()
        self._btid: int = -1

        self.threads = threads
        self._log.debug(lambda: f"Working with {threads} threads")

    @staticmethod
    def unpack_walk_forward_stages(start: date, stop: date, training: int, validation: int, testing: int) -> list[tuple[Union[tuple[date, date], None], tuple[date, date] | None]]:
        walk_forward = []
        current_start: date = start
        step: int = min(training, validation) if training > 0 and validation > 0 else training or validation

        if validation > 0:
            while True:
                train_start: date = current_start
                train_stop: date = min(train_start + relativedelta(months=training), stop) if training > 0 else None
                val_start: date = train_stop if train_stop and validation > 0 else None
                val_stop: date = val_start + relativedelta(months=validation) if val_start else None
                val_stop = min(val_stop, stop) if val_stop else None
    
                if (val_stop and val_stop > stop) or (train_stop and train_stop >= stop):
                    break
    
                walk_forward.append(((train_start, train_stop), (val_start, val_stop)))
                current_start += relativedelta(months=step)
    
        test_stop: date = stop
        test_start: date = max(start, (test_stop - relativedelta(months=testing)).replace(day=1)) if testing > 0 else None
        final_training_start: date = max(start, stop - relativedelta(months=training)).replace(day=1) if training > 0 else None
        final_training: Union[tuple[date, date], None] = (final_training_start, stop) if final_training_start else None
        final_testing: Union[tuple[date, date], None] = (test_start, test_stop) if test_start else None

        walk_forward.append((final_training, final_testing))

        return walk_forward

    @staticmethod
    def unpack_degrees_of_freedom_stages(money_parameters: Parameters, risk_parameters: Parameters, signal_parameters: Parameters, analyst_parameters: Parameters, manager_parameters: Parameters) -> list[dict]:
        def unpack_engine(engine_parameters: Parameters) -> list:
            stage_count = 0
            for stage_range, _ in engine_parameters.items():
                try:
                    _, stage_stop = [int(stage) for stage in stage_range.split("-")]
                except AttributeError:
                    stage_stop = int(stage_range)
                stage_count = max(stage_count, stage_stop)

            parameters_range = [None] * stage_count
            for stage_range, parameters in engine_parameters.items():
                try:
                    stage_start, stage_stop = [int(stage) for stage in stage_range.split("-")]
                except AttributeError:
                    stage_start = stage_stop = int(stage_range)
                
                for stage in range(stage_start, stage_stop + 1):
                    parameters_range[stage - 1] = parameters
            return parameters_range

        return [{"MoneyManagement": money_parameters, "RiskManagement": risk_parameters, "SignalManagement": signal_parameters, "AnalystManagement": analyst_parameters, "ManagerManagement": manager_parameters}
                for money_parameters, risk_parameters, signal_parameters, analyst_parameters, manager_parameters in zip(unpack_engine(money_parameters), unpack_engine(risk_parameters), unpack_engine(signal_parameters), unpack_engine(analyst_parameters), unpack_engine(manager_parameters))]

    @staticmethod
    def unpack_degrees_of_freedom_window(dof_stages: list[dict]) -> int:
        from Library.Market.Indicators import IndicatorsAPI
        def unpack_engine(engine_parameters: dict) -> int:

            def unpack_literal_window(candidate: list) -> int:
                tparams = candidate[1:]
                if not tparams:
                    return MARGIN
                return max(tparams) + MARGIN

            def unpack_technical_window(candidate: Technical) -> int:
                tparams = candidate.Parameters
                window = MARGIN
                for sublist in tparams.values():
                    window = max(window, sum([sub[1] for sub in sublist]) + MARGIN)
                return window

            max_window = 0
            for parameter_name, parameter_value in (engine_parameters or {}).items():
                if isinstance(parameter_value[0], list):
                    if len(parameter_value) == 1:
                        technical_list = parameter_value[0]
                        for technical_candidate in technical_list:
                            try:
                                for _, technical in IndicatorsAPI.find(TechnicalType(TechnicalType[technical_candidate])).items():
                                    max_window = max(max_window, unpack_technical_window(technical))
                            except KeyError:
                                technical = getattr(IndicatorsAPI, technical_candidate)
                                max_window = max(max_window, unpack_technical_window(technical))
                    else:
                        for technical_candidate in parameter_value:
                            max_window = max(max_window, unpack_literal_window(technical_candidate))
                else:
                    max_window = max(max_window, unpack_literal_window(parameter_value))
            return max_window

        return max([unpack_engine(stage["AnalystManagement"]) for stage in dof_stages])

    @staticmethod
    def pack_degrees_of_freedom_parameters(dof_stage: dict, dof_params: list[Parameters]) -> dict:
        for engine_name, engine_parameters in dof_stage.items():
            for parameter_name, parameter_value in engine_parameters.items() if engine_parameters else {}:
                if isinstance((dof_value := parameter_value[0]), str) and "Result=" in dof_value:
                    dof_id = int(dof_value.split("=")[1])
                    dof_stage[engine_name][parameter_name] = dof_params[dof_id - 1][engine_name][parameter_name]
        return dof_stage

    @staticmethod
    def unpack_coarse_to_fine_parameters(dof_stage: dict, ctf_params: list[Parameters]) -> Union[dict, None]:
        from Library.Market.Indicators import IndicatorsAPI
        ctf_runs = len(ctf_params)
        def unpack_engine(engine_name: str, engine_parameters: Parameters) -> tuple[bool, dict]:
            def unpack_combos(tid: str, tparams: dict, tconstraints: Callable) -> tuple[bool, list]:
                truns = 0
                for tparam in tparams.values():
                    truns = max(truns, len(tparam))
                if truns == 0:
                    return False, [tid]
                if truns == ctf_runs:
                    tlast = ctf_params[-1][engine_name][parameter_name]
                    return False, tlast 
                elif ctf_runs == 0:
                    sets = []
                    for trange in tparams.values():
                        start, stop, step = trange[0]
                        sets.append(np.arange(start, stop + step, step))
                else:
                    tlast = ctf_params[-1][engine_name][parameter_name]
                    sets = []
                    for pid, trange in enumerate(tparams.values(), start=1):
                        plast = tlast[pid]
                        start, stop, step = trange[ctf_runs]
                        sets.append(np.arange(plast + start, plast + stop + step, step))
                
                valid_combos = filter(lambda combo: tconstraints(*combo), itertools.product(*sets))
                return True, [[tid, *combo] for combo in valid_combos]        

            tune = False
            parameters = {}
            for parameter_name, parameter_value in (engine_parameters or {}).items():
                if isinstance(parameter_value[0], list):
                    if len(parameter_value) == 1:
                        technical_list = parameter_value[0]
                        all_combos = []
                        for technical_candidate in technical_list:
                            try:
                                for technical_id, technical in IndicatorsAPI.find(TechnicalType(TechnicalType[technical_candidate])).items():
                                    extend, combos = unpack_combos(technical_id, technical.Parameters, technical.Constraints)
                                    all_combos.extend(combos)
                                    tune = True
                            except KeyError:
                                technical = getattr(IndicatorsAPI, technical_id := technical_candidate)
                                extend, combos = unpack_combos(technical_id, technical.Parameters, technical.Constraints)
                                if extend:
                                    tune = True
                                    all_combos.extend(combos)
                                else:
                                    all_combos = combos
                        parameters[parameter_name] = all_combos
                    else:
                        tune = True
                        parameters[parameter_name] = parameter_value
                else:
                    parameters[parameter_name] = parameter_value

            return tune, parameters

        _, money_engine = unpack_engine("MoneyManagement", dof_stage["MoneyManagement"])
        _, risk_engine = unpack_engine("RiskManagement", dof_stage["RiskManagement"])
        _, signal_engine = unpack_engine("SignalManagement", dof_stage["SignalManagement"])
        analyst_tune, analyst_engine = unpack_engine("AnalystManagement", dof_stage["AnalystManagement"])
        _, manager_engine = unpack_engine("ManagerManagement", dof_stage["ManagerManagement"])
        return {"MoneyManagement": money_engine,
                "RiskManagement": risk_engine,
                "SignalManagement": signal_engine,
                "AnalystManagement": analyst_engine,
                "ManagerManagement": manager_engine} if analyst_tune else None

    @staticmethod
    def pack_coarse_to_fine_parameters(dof_stage: dict, ctf_params: Parameters) -> dict:
        engine_parameters = dof_stage[(engine_name := "AnalystManagement")]
        for parameter_name, parameter_value in engine_parameters.items() if engine_parameters else {}:
            if isinstance(parameter_value[0], list):
                dof_stage[engine_name][parameter_name] = [[ctf_params[engine_name][parameter_name][0]]]
        return dof_stage        

    @staticmethod
    def unpack_coarse_to_fine_backtests(ctf_stage: dict) -> list[dict]:
        def unpack_selected(engine_name: str, engine_parameters: dict):
            selected_parameters = {}
            for parameter_name, parameter_value in (engine_parameters or {}).items():
                if isinstance(parameter_value, list) and isinstance(parameter_value[0], list):
                    selected_parameters[(engine_name, parameter_name)] = parameter_value
                    template[engine_name][parameter_name] = None
            return selected_parameters
        def unpack_parameters(selected_parameters: dict):
            backtests = []
            for combo in itertools.product(*selected_parameters.values()):
                backtest = copy.deepcopy(template)
                for (engine_name, parameter_name), parameter_value in itertools.chain(zip(selected_parameters, combo)):
                    backtest[engine_name][parameter_name] = parameter_value
                backtests.append(backtest)
            return backtests

        template = copy.deepcopy(ctf_stage)
        return unpack_parameters({**unpack_selected("MoneyManagement", ctf_stage["MoneyManagement"]),
                                  **unpack_selected("RiskManagement", ctf_stage["RiskManagement"]),
                                  **unpack_selected("SignalManagement", ctf_stage["SignalManagement"]),
                                  **unpack_selected("AnalystManagement", ctf_stage["AnalystManagement"]),
                                  **unpack_selected("ManagerManagement", ctf_stage["ManagerManagement"])})

    def run_backtest_stage(self, parameters: Parameters, start: date, stop: date) -> tuple[int, BacktestingSystemAPI]:

        with self._btid_lock:
            self._btid += 1
            btid = self._btid

        thread = BacktestingSystemAPI(
            broker=self._broker,
            group=self._group,
            symbol=self._symbol,
            timeframe=self._timeframe,
            strategy=self._strategy_,
            parameters=parameters,
            start=start,
            stop=stop,
            account=self.account,
            spread=self.spread,
            commission=self.commission,
            swap=self.swap
        )

        thread.strategy = self._strategy_(money_management=parameters.MoneyManagement, risk_management=parameters.RiskManagement, signal_management=parameters.SignalManagement)
        from Library.Portfolio import PortfolioAPI
        thread.market = MarketAPI(analyst_management=parameters.AnalystManagement)
        thread.portfolio = PortfolioAPI(manager_management=parameters.ManagerManagement)

        thread.tick_df = self.tick_df
        thread.bar_df = self.bar_df
        thread.symbol_data = self.symbol_data
        thread.base_conversion_df = self.base_conversion_df
        thread.base_conversion_rate = self.base_conversion_rate
        thread.quote_conversion_df = self.quote_conversion_df
        thread.quote_conversion_rate = self.quote_conversion_rate
        thread.spread_fee = self.spread_fee
        thread.commission_fee = self.commission_fee
        thread.swap_buy_fee = self.swap_buy_fee
        thread.swap_sell_fee = self.swap_sell_fee
        thread.window = self.window
        thread.offset = self.offset

        with thread:
            thread.start()
            thread.join()

        return btid, thread

    def run_coarse_to_fine_stage(self, stage: dict, start: date, stop: date) -> tuple[int, float, Parameters, pl.DataFrame]:

        parameters = self.unpack_coarse_to_fine_backtests(stage)

        results: list[dict] = []

        best_id: Union[int, None] = None
        best_fitness: float = float("-inf")
        best_parameters: Union[Parameters, None] = None

        self._log.level(VerboseType.Exception)

        with ThreadPoolExecutor(max_workers=self.threads) as executor:

            futures = [executor.submit(self.run_backtest_stage, Parameters(data=params, path=self.parameters.path), start, stop) for params in parameters]

            with tqdm(total=len(futures), desc="Progress", unit=" Backtest") as progress:
                for future in as_completed(futures):
                    btid, backtest = future.result()
                    fitness = backtest.statistics.filter(pl.col(StatisticsAPI.STATISTICS_METRICS_LABEL) == self._fitness)[StatisticsAPI.TOTAL_METRICS_AGGREGATED].item()

                    results.append({
                        self.BACKTESTSTAGEID: btid,
                        self._fitness: fitness,
                        **backtest.parameters.MoneyManagement,
                        **backtest.parameters.RiskManagement,
                        **backtest.parameters.SignalManagement,
                        **backtest.parameters.AnalystManagement,
                        **backtest.parameters.ManagerManagement
                    })
    
                    if fitness is not None and fitness > best_fitness:
                        best_id = btid
                        best_fitness = fitness
                        best_parameters = backtest.parameters
                        progress.set_postfix({"Best Fitness": f"{best_fitness:.6f}", "Best Parameters": list(backtest.parameters.AnalystManagement.values())})

                    progress.update(1)

        self._log.reset()

        df = pl.DataFrame(results, strict=False)
        df = df.sort(by=self._fitness, descending=True, nulls_last=True)

        return best_id, best_fitness, best_parameters, df

    def run_degrees_of_freedom_stage(self, ctf_stage: dict, start: date, stop: date) -> tuple[int, float, Parameters, pl.DataFrame]:

        results: list[dict] = []
        parameters: list[Parameters] = []

        last_btid: Union[int, None] = None
        last_fitness: Union[float, None] = None
        last_parameters: Union[Parameters, None] = None
        last_df: Union[pl.DataFrame, None] = None

        ctf_id = 0
        while ctf_stage := self.unpack_coarse_to_fine_parameters(ctf_stage, parameters):
            ctf_id += 1
            last_btid, last_fitness, last_parameters, last_df = self.run_coarse_to_fine_stage(ctf_stage, start, stop)

            results.append({
                self.CTFSTAGEID: ctf_id,
                self.BACKTESTSTAGEID: last_btid,
                self._fitness: last_fitness,
                **last_parameters.MoneyManagement,
                **last_parameters.RiskManagement,
                **last_parameters.SignalManagement,
                **last_parameters.AnalystManagement,
                **last_parameters.ManagerManagement
            })
            parameters.append(last_parameters)

            ctf_stage = self.pack_coarse_to_fine_parameters(ctf_stage, last_parameters)

            self._log.console.info(lambda: f"Completed Coarse-to-Fine ID={ctf_id} with {last_df}")
            self._log.telegram.info(lambda: f"Completed Coarse-to-Fine ID={ctf_id}")
            self._log.telegram.info(lambda: image(last_df.head(50)))
            self._log.file.info(lambda: f"Completed Coarse-to-Fine ID={ctf_id} with {last_df}")

        ctf_df = pl.DataFrame(results, strict=False)
        ctf_df = ctf_df.sort(by=self.CTFSTAGEID, descending=True)

        return last_btid, last_fitness, last_parameters, ctf_df

    def run_optimization_stage(self, start: date, stop: date) -> tuple[int, float, Parameters, pl.DataFrame]:

        results: list[dict] = []
        parameters: list[Parameters] = []

        last_btid: Union[int, None] = None
        last_fitness: Union[float, None] = None
        last_parameters: Union[Parameters, None] = None
        last_df: Union[pl.DataFrame, None] = None

        for dof_id, dof_stage in enumerate(self._dof_stages, start=1):
            dof_stage = self.pack_degrees_of_freedom_parameters(dof_stage, parameters)
            last_btid, last_fitness, last_parameters, last_df = self.run_degrees_of_freedom_stage(dof_stage, start, stop)

            results.append({
                self.DOFSTAGEID: dof_id,
                self.BACKTESTSTAGEID: last_btid,
                self._fitness: last_fitness,
                **last_parameters.MoneyManagement,
                **last_parameters.RiskManagement,
                **last_parameters.SignalManagement,
                **last_parameters.AnalystManagement,
                **last_parameters.ManagerManagement
            })
            parameters.append(last_parameters)

            self._log.console.info(lambda: f"Completed Degrees-of-Freedom ID={dof_id} with {last_df}")
            self._log.telegram.info(lambda: f"Completed Degrees-of-Freedom ID={dof_id}")
            self._log.telegram.info(lambda: image(last_df))
            self._log.file.info(lambda: f"Completed Degrees-of-Freedom ID={dof_id} with {last_df}")

        dof_df = pl.DataFrame(results, strict=False)
        dof_df = dof_df.sort(by=self.DOFSTAGEID, descending=True)

        return last_btid, last_fitness, last_parameters, dof_df

    @timer
    def run(self) -> None:

        self._log.telegram.info(lambda: gantt(self._wf_stages))

        results: list[dict] = []

        opt_parameters = self.parameters
        for wf_id, ((opt_start, opt_stop), (val_start, val_stop)) in enumerate(self._wf_stages, start=1):
            opt_id, opt_fitness, opt_parameters, opt_df = self.run_optimization_stage(opt_start, opt_stop)
            self._log.level(VerboseType.Exception)
            val_id, val_bt = self.run_backtest_stage(opt_parameters, val_start, val_stop)
            self._log.reset()
            val_bt_fitness = val_bt.statistics.filter(pl.col(StatisticsAPI.STATISTICS_METRICS_LABEL) == self._fitness)[StatisticsAPI.TOTAL_METRICS_AGGREGATED].item()

            results.append({
                self.WFSTAGEID: wf_id,
                self.WFOPTSTART: opt_start,
                self.WFOPTSTOP: opt_stop,
                self.WFVALSTART: val_start,
                self.WFVALSTOP: val_stop,
                self.WFOPTFITNESS.format(self._fitness): opt_fitness,
                self.WFVALFITNESS.format(self._fitness): val_bt_fitness,
                **opt_parameters.MoneyManagement,
                **opt_parameters.RiskManagement,
                **opt_parameters.SignalManagement,
                **opt_parameters.AnalystManagement,
                **opt_parameters.ManagerManagement
            })

            self._log.console.info(lambda: f"Completed Walk-Forward ID={wf_id} with {opt_df}")
            self._log.telegram.info(lambda: f"Completed Walk-Forward ID={wf_id}")
            self._log.telegram.info(lambda: image(opt_df))
            self._log.file.info(lambda: f"Completed Walk-Forward ID={wf_id} with {opt_df}")

        wf_df = pl.DataFrame(results, strict=False)
        wf_df = wf_df.sort(by=self.WFSTAGEID, descending=True)

        self._log.console.info(lambda: f"Completed Optimization {wf_df}")
        self._log.telegram.info(lambda: f"Completed Optimization")
        self._log.telegram.info(lambda: image(wf_df))
        self._log.file.info(lambda: f"Completed Optimization {wf_df}")

        self.strategy = self._strategy_(
            money_management=opt_parameters.MoneyManagement,
            risk_management=opt_parameters.RiskManagement,
            signal_management=opt_parameters.SignalManagement
        )
        from Library.Indicator import IndicatorAPI
        self.market = MarketAPI(parameters=None)
        self.indicator = IndicatorAPI(parameters=opt_parameters.AnalystManagement)
        from Library.Portfolio import PortfolioAPI
        self.portfolio = PortfolioAPI(parameters=opt_parameters.ManagerManagement)

        self._log.telegram.level(VerboseType.Exception)
        super().run()
        self._log.telegram.reset()
