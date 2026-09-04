from __future__ import annotations

import json
import yaml

from abc import ABC, abstractmethod
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Sequence, Type, Union, TYPE_CHECKING

from Library.Database import BufferAPI
from Library.Database.Dataframe import pl
from Library.Logging import LoggingAPI, VerboseLevel
from Library.Market.Bar import BarAPI
from Library.Market.Tick import TickAPI
from Library.Portfolio.Account import AccountAPI
from Library.Portfolio.Order import OrderAPI
from Library.Portfolio.Position import PositionAPI, PositionStatus
from Library.Portfolio.Session import SessionAPI
from Library.Portfolio.Statistic import generate_benchmark_report, generate_net_report, order_view, position_view, trade_view, deal_view
from Library.Portfolio.Trade import TradeAPI
from Library.Protocol.Action import ActionAPI, ActionID, CompleteActionAPI, ShutdownActionAPI
from Library.Protocol.Update import (
    UpdateID,
    CompleteUpdateAPI,
    InitUpdateAPI,
    AccountUpdateAPI,
    SecurityUpdateAPI,
    ExecutionUpdateAPI,
    BarUpdateAPI,
    TickUpdateAPI,
    OpenedBuyPositionUpdateAPI,
    OpenedSellPositionUpdateAPI,
    DecreasedBuyPositionVolumeUpdateAPI,
    DecreasedSellPositionVolumeUpdateAPI,
    IncreasedBuyPositionVolumeUpdateAPI,
    IncreasedSellPositionVolumeUpdateAPI,
    ModifiedBuyPositionStopLossUpdateAPI,
    ModifiedSellPositionStopLossUpdateAPI,
    ModifiedBuyPositionTakeProfitUpdateAPI,
    ModifiedSellPositionTakeProfitUpdateAPI,
    ClosedBuyPositionUpdateAPI,
    ClosedSellPositionUpdateAPI,
    StopLossBuyPositionUpdateAPI,
    StopLossSellPositionUpdateAPI,
    TakeProfitBuyPositionUpdateAPI,
    TakeProfitSellPositionUpdateAPI,
    MarginCallBuyPositionUpdateAPI,
    MarginCallSellPositionUpdateAPI,
    OpenedBuyStopOrderUpdateAPI,
    OpenedSellStopOrderUpdateAPI,
    ModifiedBuyStopOrderVolumeUpdateAPI,
    ModifiedSellStopOrderVolumeUpdateAPI,
    ModifiedBuyStopOrderStopPriceUpdateAPI,
    ModifiedSellStopOrderStopPriceUpdateAPI,
    ModifiedBuyStopOrderStopLossUpdateAPI,
    ModifiedSellStopOrderStopLossUpdateAPI,
    ModifiedBuyStopOrderTakeProfitUpdateAPI,
    ModifiedSellStopOrderTakeProfitUpdateAPI,
    ClosedBuyStopOrderUpdateAPI,
    ClosedSellStopOrderUpdateAPI,
    FilledBuyStopOrderUpdateAPI,
    FilledSellStopOrderUpdateAPI,
    ExpiredBuyStopOrderUpdateAPI,
    ExpiredSellStopOrderUpdateAPI,
    OpenedBuyLimitOrderUpdateAPI,
    OpenedSellLimitOrderUpdateAPI,
    ModifiedBuyLimitOrderVolumeUpdateAPI,
    ModifiedSellLimitOrderVolumeUpdateAPI,
    ModifiedBuyLimitOrderLimitPriceUpdateAPI,
    ModifiedSellLimitOrderLimitPriceUpdateAPI,
    ModifiedBuyLimitOrderStopLossUpdateAPI,
    ModifiedSellLimitOrderStopLossUpdateAPI,
    ModifiedBuyLimitOrderTakeProfitUpdateAPI,
    ModifiedSellLimitOrderTakeProfitUpdateAPI,
    ClosedBuyLimitOrderUpdateAPI,
    ClosedSellLimitOrderUpdateAPI,
    FilledBuyLimitOrderUpdateAPI,
    FilledSellLimitOrderUpdateAPI,
    ExpiredBuyLimitOrderUpdateAPI,
    ExpiredSellLimitOrderUpdateAPI,
    OpenedBuyStopLimitOrderUpdateAPI,
    OpenedSellStopLimitOrderUpdateAPI,
    ModifiedBuyStopLimitOrderVolumeUpdateAPI,
    ModifiedSellStopLimitOrderVolumeUpdateAPI,
    ModifiedBuyStopLimitOrderStopPriceUpdateAPI,
    ModifiedSellStopLimitOrderStopPriceUpdateAPI,
    ModifiedBuyStopLimitOrderLimitPriceUpdateAPI,
    ModifiedSellStopLimitOrderLimitPriceUpdateAPI,
    ModifiedBuyStopLimitOrderStopLossUpdateAPI,
    ModifiedSellStopLimitOrderStopLossUpdateAPI,
    ModifiedBuyStopLimitOrderTakeProfitUpdateAPI,
    ModifiedSellStopLimitOrderTakeProfitUpdateAPI,
    ClosedBuyStopLimitOrderUpdateAPI,
    ClosedSellStopLimitOrderUpdateAPI,
    FilledBuyStopLimitOrderUpdateAPI,
    FilledSellStopLimitOrderUpdateAPI,
    ExpiredBuyStopLimitOrderUpdateAPI,
    ExpiredSellStopLimitOrderUpdateAPI,
    DeniedUpdateAPI,
    ExceptionUpdateAPI
)
from Library.System.Lifecycle import LifecycleAPI
from Library.Universe.Security import SecurityAPI
from Library.Utility.Enumeration import EnumerationAPI
from Library.Utility.Path import inspect_destination
from Library.Utility.Service import ServiceAPI
from Library.Utility.Statistic import Timer

if TYPE_CHECKING:
    from Library.Engine import MachineAPI
    from Library.Indicator.Fundamental import FundamentalAPI
    from Library.Indicator.Indicator import IndicatorAPI
    from Library.Indicator.Sentimental import SentimentalAPI
    from Library.Indicator.Technical import TechnicalAPI
    from Library.Market.Market import MarketAPI
    from Library.Utility.Parameter import Parameter
    from Library.Portfolio.Portfolio import PortfolioAPI
    from Library.Strategy.Strategy import StrategyAPI
    from Library.Universe.Timeframe import TimeframeAPI

class SystemType(EnumerationAPI):
    Live = 1
    Simulation = 2
    Testing = 3
    Backtesting = 4
    Optimization = 5
    Learning = 6

class SystemAPI(ServiceAPI, ABC):

    Exports: str = "Exports"
    Plots: str = "Plots"

    def __init__(self,
                 strategy: Type[StrategyAPI],
                 security: SecurityAPI,
                 timeframe: TimeframeAPI,
                 parameters: Parameter,
                 universe: tuple[int, float, int, int] = (0, 0.0, 0, 0),
                 market: tuple[int, float, int, int] = (0, 0.0, 0, 0),
                 portfolio: tuple[int, float, int, int] = (0, 0.0, 0, 0),
                 risk_free: float = 0.0,
                 benchmark: Union[str, Sequence, None] = None,
                 report: bool = True,
                 export: bool = True,
                 plot: bool = False,
                 run: Union[str, Path, None] = None,
                 description: Union[str, None] = None) -> None:
        super().__init__()
        self._connected_: bool = False
        self._run_: Union[Path, None] = Path(run) if run else None
        self._reporting_: bool = report
        self._exporting_: bool = export
        self._plotting_: bool = plot
        self._description_: Union[str, None] = description
        self._failures_: list = []
        self._risk_free_: float = risk_free
        self._benchmarking_: bool = benchmark is not None
        self._benchmark_: tuple = tuple(entry.strip() for entry in (benchmark.split(",") if isinstance(benchmark, str) else benchmark or ()) if entry and entry.strip())
        self._strategy_: Type[StrategyAPI] = strategy
        self._security_: SecurityAPI = security
        self._timeframe_: TimeframeAPI = timeframe
        self._parameters_: Parameter = parameters

        self.account: Union[AccountAPI, None] = None
        self.security: SecurityAPI = security
        self.market: Union[MarketAPI, None] = None
        self.indicator: Union[IndicatorAPI, None] = None
        self.technical: Union[TechnicalAPI, None] = None
        self.fundamental: Union[FundamentalAPI, None] = None
        self.sentimental: Union[SentimentalAPI, None] = None
        self.portfolio: Union[PortfolioAPI, None] = None
        self.strategy: Union[StrategyAPI, None] = None
        self.statistics = None
        self.benchmarks = None

        self._universe_: BufferAPI = BufferAPI(types=[SecurityAPI], batch=universe[0], interval=universe[1], workers=universe[2], maxsize=universe[3])
        self._market_: BufferAPI = BufferAPI(types=[TickAPI, BarAPI], batch=market[0], interval=market[1], workers=market[2], maxsize=market[3], bulk=True)
        self._portfolio_: BufferAPI = BufferAPI(types=[AccountAPI, OrderAPI, PositionAPI, TradeAPI], batch=portfolio[0], interval=portfolio[1], workers=portfolio[2], maxsize=portfolio[3])

        self._session_: Union[SessionAPI, None] = None
        self._initialization_timer_: Timer = Timer()
        self._execution_timer_: Timer = Timer()
        self._finalization_timer_: Timer = Timer()

        self._log_: LoggingAPI = LoggingAPI("System Management")

    def _attach_session_(self, record) -> None:
        if not self._portfolio_.Active or self._session_ is None: return
        record.Session = self._session_
        if not isinstance(record, AccountAPI):
            record.Account = self.account

    def connected(self) -> bool:
        return self._connected_

    def disconnected(self) -> bool:
        return not self._connected_

    def _connect_(self) -> None:
        if self.indicator is not None:
            self.technical = self.indicator.Technical
            self.fundamental = self.indicator.Fundamental
            self.sentimental = self.indicator.Sentimental
        if self._market_.Active: self._market_.start()
        if self._portfolio_.Active: self._portfolio_.start()
        self._connected_ = True

    def _disconnect_(self) -> None:
        if self._market_.Active: self._market_.shutdown()
        if self._portfolio_.Active: self._portfolio_.shutdown()
        self._connected_ = False

    def connect(self, **kwargs):
        if self._initialization_timer_._start_ is None: self._initialization_timer_.start()
        return super().connect(**kwargs)

    def disconnect(self):
        result = super().disconnect()
        if self._transition_(self._finalization_timer_, "Finalization"): self._summary_()
        return result

    def _transition_(self, timer: Timer, phase: str, start: Union[Timer, None] = None) -> bool:
        if timer._start_ is None or timer._stop_ is not None: return False
        timer.stop()
        self._log_.info(lambda: f"Phase {phase}: Completed · {timer.result()}")
        if start is not None: start.start()
        return True

    def _summary_(self) -> None:
        pass

    @staticmethod
    def _stringify_(df: pl.DataFrame) -> pl.DataFrame:
        nested = (pl.List, pl.Struct) + ((pl.Array,) if hasattr(pl, "Array") else ())
        columns = [name for name, dtype in df.schema.items() if isinstance(dtype, nested)]
        if not columns: return df
        return df.with_columns([pl.col(name).map_elements(lambda v: json.dumps(v, default=str), return_dtype=pl.Utf8).alias(name) for name in columns])

    _OUTPUT_: str = "Output"

    def _publish_(self, name: str, sections: dict) -> Union[Path, None]:
        if self._run_ is None or not sections: return None
        try:
            folder = self._run_ / self._OUTPUT_
            folder.mkdir(parents=True, exist_ok=True)
            path = folder / name
            path.write_text(yaml.safe_dump(sections, sort_keys=False), encoding="utf-8")
            self._log_.info(lambda: f"Publish Operation: Saved · {path}")
            return path
        except Exception as error:
            self._log_.warning(lambda error=error: f"Publish Operation: Failed · {error}")
            return None

    def _destination_(self, request, temporary: str, scoped: str = "") -> Union[Path, None]:
        if request is None or request is False: return None
        if request is True and self._run_ is not None: return self._run_.joinpath(self._OUTPUT_, scoped) if scoped else self._run_ / self._OUTPUT_
        return inspect_destination(request, temporary)

    def _export_(self, tables: dict) -> None:
        try:
            ident = getattr(self, "_iid_", None) or getattr(self._session_, "UID", None) or self.__class__.__name__
            destination = self._destination_(self._exporting_, self.Exports, "Export")
            if self._run_ is not None and self._exporting_ is True:
                folder = destination
                folder.mkdir(parents=True, exist_ok=True)
            else:
                base = destination / f"{datetime.now():%Y-%m-%d %H-%M-%S} {ident}"
                folder, index = base, 2
                while folder.exists():
                    folder = base.parent / f"{base.name} ({index})"
                    index += 1
                folder.mkdir(parents=True)
            for name, table in tables.items():
                try:
                    self._stringify_(table).write_csv(str(folder / f"{name.lower()}.csv"))
                except Exception as error:
                    self._log_.error(lambda n=name, e=error: f"Export Operation: Failed · {n} · {e}")
                    self._failures_.append(f"Export {name}: {error}")
            self._log_.info(lambda: f"Export Operation: Saved · {folder}")
        except Exception as error:
            self._log_.error(lambda error=error: f"Export Operation: Failed · {error}")
            self._failures_.append(f"Export: {error}")

    def _bars_(self) -> list:
        if self.market is None: return []
        frame = self.market.dataframe()
        if frame is None or frame.is_empty(): return []
        columns = ("Timestamp", "OpenTick.Bid", "HighTick.Bid", "LowTick.Bid", "CloseTick.Bid", "OpenTick.Timestamp")
        if any(column not in frame.columns for column in columns): return []
        if "Volume" in frame.columns: columns += ("Volume",)
        return list(zip(*(frame[column].to_list() for column in columns)))

    @staticmethod
    def _curves_(portfolio: PortfolioAPI) -> tuple[list, list]:
        equity = portfolio.EquityTrack
        balance = []
        trades = trade_view(portfolio.Trades)
        exit_stamp, exit_balance = str(TradeAPI.ID.ExitTimestamp), "ExitBalance"
        if not trades.is_empty() and exit_stamp in trades.columns and exit_balance in trades.columns:
            balance = [(stamp, value) for stamp, value in zip(trades[exit_stamp].to_list(), trades[exit_balance].to_list()) if stamp is not None and value is not None]
        opening = portfolio.InitialBalance
        if opening is not None and equity: balance.insert(0, (equity[0][0], opening))
        return equity, balance

    @staticmethod
    def _label_at_(stamp, bars: list):
        if stamp is None or not bars: return None
        low, high = 0, len(bars) - 1
        if stamp < bars[0][5]: return None
        while low < high:
            middle = (low + high + 1) // 2
            if bars[middle][5] <= stamp: low = middle
            else: high = middle - 1
        return bars[low][0]

    def _markers_(self, portfolio: PortfolioAPI) -> list:
        trades = trade_view(portfolio.Trades)
        if trades.is_empty(): return []
        fields = (str(TradeAPI.ID.UID), str(TradeAPI.ID.Direction), str(TradeAPI.ID.EntryTimestamp), str(TradeAPI.ID.ExitTimestamp), str(TradeAPI.ID.EntryPrice), str(TradeAPI.ID.ExitPrice), str(TradeAPI.ID.NetPnL))
        if any(field not in trades.columns for field in fields): return []
        bars = self._bars_()
        return [(row[0], str(row[1]), self._label_at_(row[2], bars), self._label_at_(row[3], bars), row[4], row[5], row[6] or 0.0) for row in zip(*(trades[field].to_list() for field in fields))]

    @staticmethod
    def _label_(security: SecurityAPI, suffix: Union[str, None] = None) -> str:
        ticker = security.Ticker if security else None
        contract = security.Contract if security else None
        kind = contract.Type if contract else None
        parts = [str(ticker.UID) if ticker and ticker.UID else "Security"]
        if ticker and ticker.Description: parts.append(str(ticker.Description))
        if kind is not None: parts.append(kind.name if hasattr(kind, "name") else str(kind))
        if suffix: parts.append(suffix)
        return " · ".join(parts)

    def _benchmarks_(self, start, stop) -> dict:
        benchmarks = {}
        bars = self._bars_()
        if bars: benchmarks[self._label_(self._security_, "Buy & Hold")] = [(bar[0], bar[4]) for bar in bars]
        database = getattr(self, "_db_", None)
        if not self._benchmark_: return benchmarks
        if database is None:
            self._log_.warning(lambda: f"Benchmark Operation: Skipped · Due to no Database connection ({' · '.join(self._benchmark_)})")
            return benchmarks
        from Library.Market.Market import MarketAPI
        from Library.Universe.Provider import ProviderAPI
        from Library.Universe.Security import SecurityAPI
        from Library.Universe.Ticker import TickerAPI
        for spec in self._benchmark_:
            try:
                provider_uid, _, ticker_uid = spec.rpartition(":")
                provider = ProviderAPI(UID=ProviderAPI.normalize(provider_uid), db=database, autoload=True) if provider_uid else self._security_.Provider
                security = SecurityAPI(Provider=provider, Ticker=TickerAPI(UID=TickerAPI.normalize(ticker_uid), db=database, autoload=True), db=database, autoload=True)
                frame = MarketAPI.pull_bars(database, security.UID, self._timeframe_.UID, start=start, stop=stop)
                if frame.is_empty(): raise ValueError(f"No {self._timeframe_.UID} Bars")
                benchmarks[self._label_(security)] = list(zip(frame["Timestamp"].to_list(), frame["CloseTick.Bid"].to_list()))
            except Exception as error:
                self._log_.warning(lambda s=spec, e=error: f"Benchmark Operation: Skipped · {s} · {e}")
        return benchmarks

    def _workspace_(self, workspace):
        return workspace

    def _analysis_(self) -> dict:
        return {}

    def _plot_(self, portfolio: PortfolioAPI, account: Union[AccountAPI, None], start, stop, benchmarks: dict, tables: dict) -> None:
        from Library.App.V2.Workspace import backtest
        equity, balance = self._curves_(portfolio)
        ticker = self._security_.Ticker.UID if self._security_ and self._security_.Ticker else "Security"
        title = f"{self.__class__.__name__} · {self._strategy_.__name__} · {ticker} {self._timeframe_.UID} · {start} → {stop}"
        workspace = backtest(
            title=title,
            description=self._description_,
            anchor=start,
            currency=account.Asset if account is not None and account.Asset else "",
            bars=self._bars_(),
            equity=equity,
            balance=balance,
            signals=self.strategy.Signals if self.strategy is not None else [],
            trades=self._markers_(portfolio),
            benchmarks=benchmarks,
            directional=(self.strategy.DirectionalEntryThreshold, self.strategy.DirectionalExitThreshold) if self.strategy is not None else None,
            volumetric=(self.strategy.VolumeEntryThreshold, self.strategy.VolumeExitThreshold) if self.strategy is not None else None,
            sheets=tables)
        workspace = self._workspace_(workspace)
        self._result_(workspace)
        if not self._plotting_: return
        destination = self._destination_(self._plotting_, self.Plots)
        naming = "Plot" if self._run_ is not None and self._plotting_ is True else f"{datetime.now():%Y-%m-%d %H-%M-%S} {ticker} {self._strategy_.__name__}"
        path = workspace.render(destination, name=naming)
        self._log_.info(lambda: f"Plot Operation: Rendered · {path}")

    def _result_(self, workspace) -> None:
        if self._run_ is None: return
        try:
            folder = self._run_ / self._OUTPUT_
            folder.mkdir(parents=True, exist_ok=True)
            path = folder / "Result.json"
            path.write_text(workspace.encode(), encoding="utf-8")
            self._log_.info(lambda: f"Result Operation: Saved · {path} · {path.stat().st_size / 1048576:.1f} MB")
        except Exception as error:
            self._log_.error(lambda error=error: f"Result Operation: Failed · {error}")
            self._failures_.append(f"Result: {error}")

    @contextmanager
    def quieted(self, level: VerboseLevel = VerboseLevel.Warning):
        if self._reporting_ or self._exporting_ or self._plotting_:
            yield self
            return
        with self._log_.console.temporary(level), self._log_.file.temporary(level): yield self

    @contextmanager
    def deliverables(self, report: bool, export: bool, plot: bool):
        restored = (self._reporting_, self._exporting_, self._plotting_)
        self._reporting_, self._exporting_, self._plotting_ = report, export, plot
        try: yield self
        finally: self._reporting_, self._exporting_, self._plotting_ = restored

    def _report_(self, portfolio: PortfolioAPI, account: Union[AccountAPI, None], start, stop) -> None:
        if portfolio is None: return
        net = generate_net_report(portfolio.Positions, portfolio.Trades, account, start, stop, portfolio.EquityCurve, portfolio.Excursions, risk_free=self._risk_free_)
        self.statistics = net
        benchmarks = {}
        try: benchmarks = self._benchmarks_(start, stop)
        except Exception as error: self._log_.error(lambda error=error: f"Benchmark Operation: Failed · {error}")
        self.benchmarks = generate_benchmark_report(portfolio.EquityTrack, benchmarks, start, stop, risk_free=self._risk_free_) if self._benchmarking_ else None
        if not (self._reporting_ or self._exporting_ or self._plotting_): return
        tables = {
            "Orders": order_view(portfolio.Orders),
            "Positions": position_view(portfolio.Positions),
            "Trades": trade_view(portfolio.Trades),
            "Deals": deal_view(portfolio.Deals),
            "Net": net,
        }
        if self.benchmarks is not None and not self.benchmarks.is_empty(): tables["Benchmark"] = self.benchmarks
        try: self._plot_(portfolio, account, start, stop, benchmarks, tables)
        except Exception as error:
            self._log_.error(lambda error=error: f"Plot Operation: Failed · {error}")
            self._failures_.append(f"Plot: {error}")
        if self._reporting_:
            for name, table in tables.items():
                if table.is_empty(): continue
                self._log_.info(lambda n=name, t=table: f"Report {n}: {t}")
            for name, frame in self._analysis_().items():
                self._log_.info(lambda n=name, t=frame: f"Report {n}: {t}")
        if self._exporting_:
            self._export_(tables)
        self._delivered_()

    def _identity_(self) -> str:
        ticker = getattr(getattr(self._security_, "Ticker", None), "UID", None) or "Security"
        frame = getattr(self._timeframe_, "UID", None)
        return f"{ticker} {frame}" if frame else ticker

    def _delivered_(self) -> None:
        if not self._failures_: return
        summary = " · ".join(self._failures_)
        self._failures_ = []
        raise RuntimeError(f"Output Operation: Failed · {summary}")

    @abstractmethod
    def send_action(self, action: ActionAPI) -> None:
        raise NotImplementedError

    @abstractmethod
    def receive_update_id(self) -> UpdateID:
        raise NotImplementedError

    @abstractmethod
    def _receive_update_init_(self, offset: int = 1) -> InitUpdateAPI:
        raise NotImplementedError

    @abstractmethod
    def receive_update_account(self, offset: int = 1) -> AccountAPI:
        raise NotImplementedError

    def _receive_update_account_(self) -> AccountAPI:
        account = self.receive_update_account()
        self._attach_session_(account)
        if self._portfolio_.Active and self._session_ is not None and self._session_.InitialAccount is None:
            account.save()
            self._session_.InitialAccount = account
            self._session_.save()
        else:
            self._portfolio_.add(account)
        return account

    @abstractmethod
    def receive_update_security(self, offset: int = 1) -> SecurityAPI:
        raise NotImplementedError

    def _receive_update_security_(self) -> SecurityAPI:
        security = self.receive_update_security()
        if self._universe_.Active: security.save()
        return security

    @abstractmethod
    def receive_update_tick(self, offset: int = 1) -> TickAPI:
        raise NotImplementedError

    def _receive_update_tick_(self) -> TickAPI:
        tick = self.receive_update_tick()
        self._market_.add(tick)
        return tick

    @abstractmethod
    def receive_update_bar(self, offset: int = 1) -> BarAPI:
        raise NotImplementedError

    def _receive_update_bar_(self) -> BarAPI:
        bar = self.receive_update_bar()
        self._market_.add(bar.GapTick)
        self._market_.add(bar.OpenTick)
        self._market_.add(bar.HighTick)
        self._market_.add(bar.LowTick)
        self._market_.add(bar.CloseTick)
        self._market_.add(bar)
        return bar

    @abstractmethod
    def receive_update_order(self, offset: int = 1) -> OrderAPI:
        raise NotImplementedError

    def _receive_update_order_(self) -> OrderAPI:
        order = self.receive_update_order()
        self._attach_session_(order)
        self._portfolio_.add(order)
        return order

    @abstractmethod
    def receive_update_position(self, offset: int = 1) -> PositionAPI:
        raise NotImplementedError

    def _receive_update_position_(self) -> PositionAPI:
        position = self.receive_update_position()
        self._attach_session_(position)
        self._portfolio_.add(position)
        return position

    @abstractmethod
    def receive_update_trade(self, offset: int = 1) -> TradeAPI:
        raise NotImplementedError

    @abstractmethod
    def receive_update_position_trade(self, offset: int = 1) -> tuple[PositionAPI, TradeAPI]:
        raise NotImplementedError

    def _receive_update_position_trade_(self, status: PositionStatus) -> tuple[PositionAPI, TradeAPI]:
        pos, trade = self.receive_update_position_trade()
        pos.Status = status
        self._attach_session_(pos)
        self._attach_session_(trade)
        self._portfolio_.add(pos)
        self._portfolio_.add(trade)
        return pos, trade

    def _receive_update_trade_(self) -> TradeAPI:
        trade = self.receive_update_trade()
        self._attach_session_(trade)
        self._portfolio_.add(trade)
        return trade

    @abstractmethod
    def receive_update_denied(self, offset: int = 1) -> tuple[ActionID, str]:
        raise NotImplementedError

    @abstractmethod
    def receive_update_exception(self, offset: int = 1) -> str:
        raise NotImplementedError

    @abstractmethod
    def system_management(self) -> MachineAPI:
        raise NotImplementedError

    def _process_updates_(self, engine: LifecycleAPI) -> list[ActionAPI]:
        actions: list[ActionAPI] = []
        while True:
            if not self._universe_.Empty: self._universe_.flush()
            if not self._market_.Empty: self._market_.flush()
            if not self._portfolio_.Empty: self._portfolio_.flush()
            update_id = self.receive_update_id()
            match update_id:
                case UpdateID.Init:
                    actions += engine.perform(update_id, self._receive_update_init_())
                case UpdateID.Complete:
                    actions += engine.perform(update_id, CompleteUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio))
                    return actions
                case UpdateID.Shutdown:
                    actions += engine.perform(update_id, CompleteUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio))
                    return actions
                case UpdateID.Account:
                    self.account = self._receive_update_account_()
                    actions += engine.perform(update_id, AccountUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio))
                case UpdateID.Security:
                    self.security = self._receive_update_security_()
                    actions += engine.perform(update_id, SecurityUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio))
                case UpdateID.Execution:
                    actions += engine.perform(update_id, ExecutionUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio))
                case UpdateID.Tick:
                    actions += engine.perform(update_id, TickUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Tick=self._receive_update_tick_()))
                case UpdateID.BarOpened:
                    actions += engine.perform(update_id, BarUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_()))
                case UpdateID.BarClosed:
                    actions += engine.perform(update_id, BarUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_()))
                case UpdateID.AskAboveTarget:
                    actions += engine.perform(update_id, TickUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Tick=self._receive_update_tick_()))
                case UpdateID.AskBelowTarget:
                    actions += engine.perform(update_id, TickUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Tick=self._receive_update_tick_()))
                case UpdateID.BidAboveTarget:
                    actions += engine.perform(update_id, TickUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Tick=self._receive_update_tick_()))
                case UpdateID.BidBelowTarget:
                    actions += engine.perform(update_id, TickUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Tick=self._receive_update_tick_()))
                case UpdateID.OpenedBuyPosition:
                    actions += engine.perform(update_id, OpenedBuyPositionUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Position=self._receive_update_position_()))
                case UpdateID.OpenedSellPosition:
                    actions += engine.perform(update_id, OpenedSellPositionUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Position=self._receive_update_position_()))
                case UpdateID.DecreasedBuyPositionVolume:
                    pos, trade = self._receive_update_position_trade_(PositionStatus.Opened)
                    actions += engine.perform(update_id, DecreasedBuyPositionVolumeUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Position=pos, Trade=trade))
                case UpdateID.DecreasedSellPositionVolume:
                    pos, trade = self._receive_update_position_trade_(PositionStatus.Opened)
                    actions += engine.perform(update_id, DecreasedSellPositionVolumeUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Position=pos, Trade=trade))
                case UpdateID.IncreasedBuyPositionVolume:
                    actions += engine.perform(update_id, IncreasedBuyPositionVolumeUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Position=self._receive_update_position_()))
                case UpdateID.IncreasedSellPositionVolume:
                    actions += engine.perform(update_id, IncreasedSellPositionVolumeUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Position=self._receive_update_position_()))
                case UpdateID.ModifiedBuyPositionStopLoss:
                    actions += engine.perform(update_id, ModifiedBuyPositionStopLossUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Position=self._receive_update_position_()))
                case UpdateID.ModifiedSellPositionStopLoss:
                    actions += engine.perform(update_id, ModifiedSellPositionStopLossUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Position=self._receive_update_position_()))
                case UpdateID.ModifiedBuyPositionTakeProfit:
                    actions += engine.perform(update_id, ModifiedBuyPositionTakeProfitUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Position=self._receive_update_position_()))
                case UpdateID.ModifiedSellPositionTakeProfit:
                    actions += engine.perform(update_id, ModifiedSellPositionTakeProfitUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Position=self._receive_update_position_()))
                case UpdateID.ClosedBuyPosition:
                    pos, trade = self._receive_update_position_trade_(PositionStatus.Closed)
                    actions += engine.perform(update_id, ClosedBuyPositionUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Position=pos, Trade=trade))
                case UpdateID.ClosedSellPosition:
                    pos, trade = self._receive_update_position_trade_(PositionStatus.Closed)
                    actions += engine.perform(update_id, ClosedSellPositionUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Position=pos, Trade=trade))
                case UpdateID.StopLossBuyPosition:
                    pos, trade = self._receive_update_position_trade_(PositionStatus.Closed)
                    actions += engine.perform(update_id, StopLossBuyPositionUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Position=pos, Trade=trade))
                case UpdateID.StopLossSellPosition:
                    pos, trade = self._receive_update_position_trade_(PositionStatus.Closed)
                    actions += engine.perform(update_id, StopLossSellPositionUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Position=pos, Trade=trade))
                case UpdateID.TakeProfitBuyPosition:
                    pos, trade = self._receive_update_position_trade_(PositionStatus.Closed)
                    actions += engine.perform(update_id, TakeProfitBuyPositionUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Position=pos, Trade=trade))
                case UpdateID.TakeProfitSellPosition:
                    pos, trade = self._receive_update_position_trade_(PositionStatus.Closed)
                    actions += engine.perform(update_id, TakeProfitSellPositionUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Position=pos, Trade=trade))
                case UpdateID.MarginCallBuyPosition:
                    pos, trade = self._receive_update_position_trade_(PositionStatus.Closed)
                    actions += engine.perform(update_id, MarginCallBuyPositionUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Position=pos, Trade=trade))
                case UpdateID.MarginCallSellPosition:
                    pos, trade = self._receive_update_position_trade_(PositionStatus.Closed)
                    actions += engine.perform(update_id, MarginCallSellPositionUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Position=pos, Trade=trade))
                case UpdateID.OpenedBuyStopOrder:
                    actions += engine.perform(update_id, OpenedBuyStopOrderUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Order=self._receive_update_order_()))
                case UpdateID.OpenedSellStopOrder:
                    actions += engine.perform(update_id, OpenedSellStopOrderUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Order=self._receive_update_order_()))
                case UpdateID.ModifiedBuyStopOrderVolume:
                    actions += engine.perform(update_id, ModifiedBuyStopOrderVolumeUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Order=self._receive_update_order_()))
                case UpdateID.ModifiedSellStopOrderVolume:
                    actions += engine.perform(update_id, ModifiedSellStopOrderVolumeUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Order=self._receive_update_order_()))
                case UpdateID.ModifiedBuyStopOrderStopPrice:
                    actions += engine.perform(update_id, ModifiedBuyStopOrderStopPriceUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Order=self._receive_update_order_()))
                case UpdateID.ModifiedSellStopOrderStopPrice:
                    actions += engine.perform(update_id, ModifiedSellStopOrderStopPriceUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Order=self._receive_update_order_()))
                case UpdateID.ModifiedBuyStopOrderStopLoss:
                    actions += engine.perform(update_id, ModifiedBuyStopOrderStopLossUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Order=self._receive_update_order_()))
                case UpdateID.ModifiedSellStopOrderStopLoss:
                    actions += engine.perform(update_id, ModifiedSellStopOrderStopLossUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Order=self._receive_update_order_()))
                case UpdateID.ModifiedBuyStopOrderTakeProfit:
                    actions += engine.perform(update_id, ModifiedBuyStopOrderTakeProfitUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Order=self._receive_update_order_()))
                case UpdateID.ModifiedSellStopOrderTakeProfit:
                    actions += engine.perform(update_id, ModifiedSellStopOrderTakeProfitUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Order=self._receive_update_order_()))
                case UpdateID.ClosedBuyStopOrder:
                    actions += engine.perform(update_id, ClosedBuyStopOrderUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Order=self._receive_update_order_()))
                case UpdateID.ClosedSellStopOrder:
                    actions += engine.perform(update_id, ClosedSellStopOrderUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Order=self._receive_update_order_()))
                case UpdateID.FilledBuyStopOrder:
                    actions += engine.perform(update_id, FilledBuyStopOrderUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Order=self._receive_update_order_()))
                case UpdateID.FilledSellStopOrder:
                    actions += engine.perform(update_id, FilledSellStopOrderUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Order=self._receive_update_order_()))
                case UpdateID.ExpiredBuyStopOrder:
                    actions += engine.perform(update_id, ExpiredBuyStopOrderUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Order=self._receive_update_order_()))
                case UpdateID.ExpiredSellStopOrder:
                    actions += engine.perform(update_id, ExpiredSellStopOrderUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Order=self._receive_update_order_()))
                case UpdateID.OpenedBuyLimitOrder:
                    actions += engine.perform(update_id, OpenedBuyLimitOrderUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Order=self._receive_update_order_()))
                case UpdateID.OpenedSellLimitOrder:
                    actions += engine.perform(update_id, OpenedSellLimitOrderUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Order=self._receive_update_order_()))
                case UpdateID.ModifiedBuyLimitOrderVolume:
                    actions += engine.perform(update_id, ModifiedBuyLimitOrderVolumeUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Order=self._receive_update_order_()))
                case UpdateID.ModifiedSellLimitOrderVolume:
                    actions += engine.perform(update_id, ModifiedSellLimitOrderVolumeUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Order=self._receive_update_order_()))
                case UpdateID.ModifiedBuyLimitOrderLimitPrice:
                    actions += engine.perform(update_id, ModifiedBuyLimitOrderLimitPriceUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Order=self._receive_update_order_()))
                case UpdateID.ModifiedSellLimitOrderLimitPrice:
                    actions += engine.perform(update_id, ModifiedSellLimitOrderLimitPriceUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Order=self._receive_update_order_()))
                case UpdateID.ModifiedBuyLimitOrderStopLoss:
                    actions += engine.perform(update_id, ModifiedBuyLimitOrderStopLossUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Order=self._receive_update_order_()))
                case UpdateID.ModifiedSellLimitOrderStopLoss:
                    actions += engine.perform(update_id, ModifiedSellLimitOrderStopLossUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Order=self._receive_update_order_()))
                case UpdateID.ModifiedBuyLimitOrderTakeProfit:
                    actions += engine.perform(update_id, ModifiedBuyLimitOrderTakeProfitUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Order=self._receive_update_order_()))
                case UpdateID.ModifiedSellLimitOrderTakeProfit:
                    actions += engine.perform(update_id, ModifiedSellLimitOrderTakeProfitUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Order=self._receive_update_order_()))
                case UpdateID.ClosedBuyLimitOrder:
                    actions += engine.perform(update_id, ClosedBuyLimitOrderUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Order=self._receive_update_order_()))
                case UpdateID.ClosedSellLimitOrder:
                    actions += engine.perform(update_id, ClosedSellLimitOrderUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Order=self._receive_update_order_()))
                case UpdateID.FilledBuyLimitOrder:
                    actions += engine.perform(update_id, FilledBuyLimitOrderUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Order=self._receive_update_order_()))
                case UpdateID.FilledSellLimitOrder:
                    actions += engine.perform(update_id, FilledSellLimitOrderUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Order=self._receive_update_order_()))
                case UpdateID.ExpiredBuyLimitOrder:
                    actions += engine.perform(update_id, ExpiredBuyLimitOrderUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Order=self._receive_update_order_()))
                case UpdateID.ExpiredSellLimitOrder:
                    actions += engine.perform(update_id, ExpiredSellLimitOrderUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Order=self._receive_update_order_()))
                case UpdateID.OpenedBuyStopLimitOrder:
                    actions += engine.perform(update_id, OpenedBuyStopLimitOrderUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Order=self._receive_update_order_()))
                case UpdateID.OpenedSellStopLimitOrder:
                    actions += engine.perform(update_id, OpenedSellStopLimitOrderUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Order=self._receive_update_order_()))
                case UpdateID.ModifiedBuyStopLimitOrderVolume:
                    actions += engine.perform(update_id, ModifiedBuyStopLimitOrderVolumeUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Order=self._receive_update_order_()))
                case UpdateID.ModifiedSellStopLimitOrderVolume:
                    actions += engine.perform(update_id, ModifiedSellStopLimitOrderVolumeUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Order=self._receive_update_order_()))
                case UpdateID.ModifiedBuyStopLimitOrderStopPrice:
                    actions += engine.perform(update_id, ModifiedBuyStopLimitOrderStopPriceUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Order=self._receive_update_order_()))
                case UpdateID.ModifiedSellStopLimitOrderStopPrice:
                    actions += engine.perform(update_id, ModifiedSellStopLimitOrderStopPriceUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Order=self._receive_update_order_()))
                case UpdateID.ModifiedBuyStopLimitOrderLimitPrice:
                    actions += engine.perform(update_id, ModifiedBuyStopLimitOrderLimitPriceUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Order=self._receive_update_order_()))
                case UpdateID.ModifiedSellStopLimitOrderLimitPrice:
                    actions += engine.perform(update_id, ModifiedSellStopLimitOrderLimitPriceUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Order=self._receive_update_order_()))
                case UpdateID.ModifiedBuyStopLimitOrderStopLoss:
                    actions += engine.perform(update_id, ModifiedBuyStopLimitOrderStopLossUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Order=self._receive_update_order_()))
                case UpdateID.ModifiedSellStopLimitOrderStopLoss:
                    actions += engine.perform(update_id, ModifiedSellStopLimitOrderStopLossUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Order=self._receive_update_order_()))
                case UpdateID.ModifiedBuyStopLimitOrderTakeProfit:
                    actions += engine.perform(update_id, ModifiedBuyStopLimitOrderTakeProfitUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Order=self._receive_update_order_()))
                case UpdateID.ModifiedSellStopLimitOrderTakeProfit:
                    actions += engine.perform(update_id, ModifiedSellStopLimitOrderTakeProfitUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Order=self._receive_update_order_()))
                case UpdateID.ClosedBuyStopLimitOrder:
                    actions += engine.perform(update_id, ClosedBuyStopLimitOrderUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Order=self._receive_update_order_()))
                case UpdateID.ClosedSellStopLimitOrder:
                    actions += engine.perform(update_id, ClosedSellStopLimitOrderUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Order=self._receive_update_order_()))
                case UpdateID.FilledBuyStopLimitOrder:
                    actions += engine.perform(update_id, FilledBuyStopLimitOrderUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Order=self._receive_update_order_()))
                case UpdateID.FilledSellStopLimitOrder:
                    actions += engine.perform(update_id, FilledSellStopLimitOrderUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Order=self._receive_update_order_()))
                case UpdateID.ExpiredBuyStopLimitOrder:
                    actions += engine.perform(update_id, ExpiredBuyStopLimitOrderUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Order=self._receive_update_order_()))
                case UpdateID.ExpiredSellStopLimitOrder:
                    actions += engine.perform(update_id, ExpiredSellStopLimitOrderUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Bar=self._receive_update_bar_(), Order=self._receive_update_order_()))
                case UpdateID.Denied:
                    action_id, reason = self.receive_update_denied()
                    actions += engine.perform(update_id, DeniedUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, ActionID=action_id, Reason=reason))
                case UpdateID.Exception:
                    reason = self.receive_update_exception()
                    actions += engine.perform(update_id, ExceptionUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, Reason=reason))

    def _process_actions_(self, actions: list[ActionAPI], terminated: bool = False) -> None:
        for action in actions: self.send_action(action)
        self.send_action(ShutdownActionAPI() if terminated else CompleteActionAPI())

    def deploy(self) -> None:
        if self.strategy is None: return
        self._strategy_.Recording = self._plotting_
        self.strategy.Signals = []
        self.strategy._long_bars_ = 0
        self.strategy._short_bars_ = 0
        engine = LifecycleAPI(
            system_machine=self.system_management(),
            strategy_machine=self.strategy.strategy_management(),
            signal_machine=self.strategy.signal_management(),
            risk_machine=self.strategy.risk_management()
        )
        while not engine.IsTerminated:
            actions = self._process_updates_(engine)
            self._process_actions_(actions, engine.IsTerminated)
            if not self._universe_.Empty: self._universe_.flush()
            if not self._market_.Empty: self._market_.flush()
            if not self._portfolio_.Empty: self._portfolio_.flush()

    @abstractmethod
    def run(self) -> None:
        raise NotImplementedError

__all__ = ["SystemType", "SystemAPI"]