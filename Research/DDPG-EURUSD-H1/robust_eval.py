import os, sys, copy, statistics
from pathlib import Path

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"): stream.reconfigure(encoding="utf-8", errors="replace")
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
sys.path.insert(0, r"C:\Users\Admin\OneDrive\Documents\cAlgo")
os.chdir(r"C:\Users\Admin\OneDrive\Documents\cAlgo")

import yaml
from datetime import datetime
from Library.Database.Postgres.Postgres import PostgresDatabaseAPI
from Library.Database.Dataframe import pl
from Library.Market.Market import MarketAPI
from Library.Portfolio.Statistic import MAXEQUITYDRAWDOWNPERC, NET_TOTAL_AGGREGATED, SHARPERATIO, SORTINORATIO, STATISTICS_METRICS_LABEL
from Library.Logging import HandlerLoggingAPI, VerboseLevel
from Library.Parameter import Parameter
from Library.Strategy.Hybrid.DDPG import DDPGStrategyAPI
from Library.System.Backtesting import BacktestingAPI
from Library.Universe.Provider import ProviderAPI
from Library.Universe.Ticker import TickerAPI
from Library.Universe.Timeframe import TimeframeAPI
from Library.Universe.Security import SecurityAPI
from Library.Universe.Contract import CommissionType, SpreadType, SwapType
from Library.Utility.Typing import MISSING

MODEL = Path(sys.argv[1])
NAME = sys.argv[2] if len(sys.argv) > 2 else MODEL.parent.name
NET = sys.argv[3] if len(sys.argv) > 3 else "64x32"
THR = float(sys.argv[4]) if len(sys.argv) > 4 else 0.0
SMOOTH = float(sys.argv[5]) if len(sys.argv) > 5 else 0.0
ACCOUNT = sys.argv[6] != "0" if len(sys.argv) > 6 else True
COMM = float(sys.argv[7]) if len(sys.argv) > 7 else 0.0
SLOW = sys.argv[8] if len(sys.argv) > 8 else "0"
INTERVAL = int(sys.argv[9]) if len(sys.argv) > 9 else 1
RISK = float(sys.argv[10]) if len(sys.argv) > 10 else 1.0
_custom = os.environ.get("ROBUST_BALANCES")
BALANCES = tuple(float(v) for v in _custom.split(",")) if _custom else ((10000.0,) if os.environ.get("ROBUST_FAST") == "1" else (9900.0, 10000.0, 10050.0, 10100.0, 10200.0))
H1, H2 = (int(x) for x in NET.split("x"))

YML = Path("Library/Parameter/Spotware(cTrader)/Forex(Major)/EURUSD/Hour/Learning.yml")
BASE = yaml.safe_load(YML.read_text(encoding="utf-8"))["DDPG"]

def node_for():
    node = copy.deepcopy(BASE)
    mm = node["MoneyManagement"]; mm["RiskPercentage"] = [RISK]; mm["ATRScale"] = [1.5]
    sm = node["SignalManagement"]
    sm["HiddenShape1"] = [H1]; sm["HiddenShape2"] = [H2]; sm["ObservationWindow"] = [1]
    sm["DirectionalEntryThreshold"] = [-THR, THR]; sm["DirectionalExitThreshold"] = [-THR, THR]
    sm["VolumeEntryThreshold"] = None; sm["VolumeExitThreshold"] = None
    sm.pop("Weights", None)
    if SMOOTH > 0.0: sm["SignalSmoothing"] = [SMOOTH]
    if INTERVAL > 1: sm["DecisionInterval"] = [INTERVAL]
    _sched = os.environ.get("ROBUST_SCHEDULE")
    if _sched: sm["DecisionSchedule"] = [_sched]
    if not ACCOUNT: sm["AccountFeatures"] = [False]
    _reb = float(os.environ.get("ROBUST_REBALANCE", "0"))
    if _reb > 0: sm["RebalanceThreshold"] = [_reb]
    if SLOW != "0":
        tm = node["TechnicalManagement"]
        tm["MOMRegime"] = ["ROC", 1440]
        tm["MOMEpoch"] = ["ROC", 2880]
        tm["MARegime"] = ["SMA", 1440]
        tm["MAEpoch"] = ["SMA", 2880]
        if SLOW == "2":
            tm["MACycle"] = ["SMA", 4320]
            tm["MAEra"] = ["SMA", 5040]
    node["PortfolioManagement"] = {"PositionMode": ["Netting"]}
    return node

HandlerLoggingAPI(Class="Robust", Subclass="Eval").set_verbose_level(VerboseLevel.Warning)
DDPGStrategyAPI.Weights = MODEL
rows = []
try:
    with PostgresDatabaseAPI(database="Quant") as db:
        ticker = TickerAPI(UID="EURUSD", db=db, autoload=True)
        provider = ProviderAPI(UID="Spotware(cTrader)", db=db, autoload=True)
        timeframe = TimeframeAPI(UID="H1", db=db, autoload=True)
        security = SecurityAPI(Provider=provider, Ticker=ticker, db=db, autoload=True)
        for initial in BALANCES:
            bt = BacktestingAPI(strategy=DDPGStrategyAPI, security=security, timeframe=timeframe, resolution=timeframe,
                                parameters=Parameter(node_for(), str(MODEL / "Robust.yml")), start=os.environ.get("ROBUST_START", "2015-01-01"), stop=os.environ.get("ROBUST_STOP", "2026-01-01"),
                                account=("EUR", initial, 30.0), spread=(SpreadType.Accurate, MISSING),
                                commission=(CommissionType.Points, COMM), swap=(SwapType.Points, float(os.environ.get("ROBUST_SWAP_LONG", "0")), float(os.environ.get("ROBUST_SWAP_SHORT", "0"))),
                                benchmark=None, report=False, export=False, plot=True, description=f"robust {NAME}")
            bt._plot_ = lambda *arguments, **keywords: None
            with bt:
                bt.run()
                ret = (bt.portfolio.Equity / initial - 1.0) * 100.0
                signals = bt.strategy.Signals
                drawdown = sharpe = sortino = 0.0
                measured = bt.statistics
                if measured is not None and not measured.is_empty() and STATISTICS_METRICS_LABEL in measured.columns:
                    row = measured.filter(pl.col(STATISTICS_METRICS_LABEL) == MAXEQUITYDRAWDOWNPERC)
                    if row.height and row[NET_TOTAL_AGGREGATED].item() is not None: drawdown = float(row[NET_TOTAL_AGGREGATED].item())
                    for label, name in ((SHARPERATIO, "sharpe"), (SORTINORATIO, "sortino")):
                        hit = measured.filter(pl.col(STATISTICS_METRICS_LABEL) == label)
                        if hit.height and hit[NET_TOTAL_AGGREGATED].item() is not None:
                            if name == "sharpe": sharpe = float(hit[NET_TOTAL_AGGREGATED].item())
                            else: sortino = float(hit[NET_TOTAL_AGGREGATED].item())
            exps = [float(r[3]) for r in signals]
            lb = sum(1 for e in exps if e > 0.0); sb = sum(1 for e in exps if e < 0.0)
            xr = min(lb, sb) / max(lb, sb) if max(lb, sb) else 0.0
            longfrac = 100.0 * lb / len(exps) if exps else 0.0
            trades = sum(1 for r in signals if abs(float(r[4])) > 0.0)
            rows.append((initial, ret, longfrac, xr, trades, drawdown, sharpe, sortino))
            print(f"ROBUST {NAME} · initial {initial:.0f} · return {ret:+8.2f}% · long {longfrac:5.1f}% · xr {xr:.2f} · trades {trades} · maxDD {drawdown:.1f}% · Sharpe {sharpe:.3f}", flush=True)
            if initial == BALANCES[0] or len(BALANCES) == 1: reference = list(signals)
        frame = MarketAPI.pull_bars(db, security.UID, timeframe.UID, start=datetime(2015, 1, 1), stop=datetime(2026, 1, 1)).to_pandas()
finally:
    DDPGStrategyAPI.Weights = None

rets = [r[1] for r in rows]
longs = [r[2] for r in rows]
mean = statistics.mean(rets)
sd = statistics.pstdev(rets) if len(rets) > 1 else 0.0
positive = sum(1 for r in rets if r > 0)
lmean = statistics.mean(longs)
verdict = "ROBUST-POSITIVE" if mean > 0 and positive >= 4 else ("MEAN-POSITIVE" if mean > 0 else "NEGATIVE")
balanced = "BALANCED-OK" if 30.0 <= lmean <= 60.0 else ("TOO-SHORT" if lmean < 30.0 else "TOO-LONG")
print(f"ROBUST {NAME} · === mean {mean:+.2f}% · sd {sd:.2f} · min {min(rets):+.2f}% · max {max(rets):+.2f}% · positive {positive}/{len(rets)} · longfrac {lmean:.1f}% · maxDD {statistics.mean([r[5] for r in rows]):.1f}% · Sharpe {statistics.mean([r[6] for r in rows]):.3f} · Sortino {statistics.mean([r[7] for r in rows]):.3f} · {verdict} · {balanced} ===", flush=True)

prices = {ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else ts: float(px) for ts, px in zip(frame["Timestamp"], frame["CloseTick.Bid"])}
years = sorted({stamp.year for stamp, *_ in reference})
yearly = {}
for year in years:
    inside = [prices[s] for s, *_ in reference if s.year == year and s in prices]
    if len(inside) > 100: yearly[year] = (inside[-1] / inside[0] - 1.0) * 100.0
weighted, total = 0.0, 0.0
print(f"ROBUST {NAME} · === REGIME ALIGNMENT (does it hold long in up-years / short in down-years) ===", flush=True)
for year, move in yearly.items():
    exps = [float(row[3]) for row in reference if row[0].year == year]
    lb = sum(1 for e in exps if e > 0.0); sb = sum(1 for e in exps if e < 0.0)
    frac = lb / (lb + sb) if (lb + sb) else 0.0
    aligned = frac if move > 0 else 1.0 - frac
    weighted += aligned * abs(move); total += abs(move)
    print(f"ROBUST {NAME} ·   {year} market {move:+6.2f}% · long {frac*100:5.1f}% · aligned {aligned*100:5.1f}% {'OK' if aligned > 0.5 else 'MISS'}", flush=True)
parts = {}
for label, span in (("train-era 2015-2023", range(2015, 2024)), ("recent 2024-2025", range(2024, 2026))):
    num = den = 0.0
    for year, move in yearly.items():
        if year not in span: continue
        exps = [float(row[3]) for row in reference if row[0].year == year]
        lb = sum(1 for e in exps if e > 0.0); sb = sum(1 for e in exps if e < 0.0)
        frac = lb / (lb + sb) if (lb + sb) else 0.0
        num += (frac if move > 0 else 1.0 - frac) * abs(move); den += abs(move)
    parts[label] = 100.0 * num / den if den else 0.0
print(f"ROBUST {NAME} · === SPLIT regime: " + " · ".join(f"{k} {v:.1f}%" for k, v in parts.items()) + " ===", flush=True)
score = weighted / total if total else 0.0
print(f"ROBUST {NAME} · === REGIME SCORE {score*100:.1f}% (50 = coin flip · >55 = real regime skill) · b&h benchmark -2.93% ===", flush=True)
