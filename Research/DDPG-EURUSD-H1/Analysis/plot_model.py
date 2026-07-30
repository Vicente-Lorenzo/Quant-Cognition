import os, sys, copy
from pathlib import Path

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"): stream.reconfigure(encoding="utf-8", errors="replace")
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
sys.path.insert(0, r"C:\Users\Admin\OneDrive\Documents\cAlgo")
os.chdir(r"C:\Users\Admin\OneDrive\Documents\cAlgo")

import yaml
from Library.Database.Postgres.Postgres import PostgresDatabaseAPI
from Library.Logging import LoggingAPI, VerboseLevel
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
NET = sys.argv[2] if len(sys.argv) > 2 else "64x32"
THR = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
COMM = float(sys.argv[4]) if len(sys.argv) > 4 else 0.0
DESC = sys.argv[5] if len(sys.argv) > 5 else f"DDPG EURUSD H1 · {MODEL.name}"
H1, H2 = (int(x) for x in NET.split("x"))

YML = Path("Library/Parameter/Spotware(cTrader)/Forex(Major)/EURUSD/Hour/Learning.yml")
BASE = yaml.safe_load(YML.read_text(encoding="utf-8"))["DDPG"]
node = copy.deepcopy(BASE)
mm = node["MoneyManagement"]; mm["RiskPercentage"] = [float(os.environ.get("PLOT_RISK", "1.0"))]; mm["ATRScale"] = [1.5]
sm = node["SignalManagement"]
sm["HiddenShape1"] = [H1]; sm["HiddenShape2"] = [H2]; sm["ObservationWindow"] = [1]
band = [-THR, THR]
sm["DirectionalEntryThreshold"] = band; sm["DirectionalExitThreshold"] = band
sm["VolumeEntryThreshold"] = None; sm["VolumeExitThreshold"] = None
sm.pop("Weights", None)
if os.environ.get("PLOT_ACCOUNT", "1") == "0": sm["AccountFeatures"] = [False]
_reb = float(os.environ.get("PLOT_REBALANCE", "0"))
if _reb > 0: sm["RebalanceThreshold"] = [_reb]
interval = int(os.environ.get("PLOT_INTERVAL", "1"))
if interval > 1: sm["DecisionInterval"] = [interval]
_sched = os.environ.get("PLOT_SCHEDULE")
if _sched: sm["DecisionSchedule"] = [_sched]
slow = os.environ.get("PLOT_SLOW", "0")
if slow != "0":
    tm = node["TechnicalManagement"]
    tm["MOMRegime"] = ["ROC", 1440]
    tm["MOMEpoch"] = ["ROC", 2880]
    tm["MARegime"] = ["SMA", 1440]
    tm["MAEpoch"] = ["SMA", 2880]
    if slow == "2":
        tm["MACycle"] = ["SMA", 4320]
        tm["MAEra"] = ["SMA", 5040]
node["PortfolioManagement"] = {"PositionMode": ["Netting"]}

LoggingAPI().set_level(VerboseLevel.Warning)
DDPGStrategyAPI.Weights = MODEL
try:
    with PostgresDatabaseAPI(database="Quant") as db:
        ticker = TickerAPI(UID="EURUSD", db=db, autoload=True)
        provider = ProviderAPI(UID="Spotware(cTrader)", db=db, autoload=True)
        timeframe = TimeframeAPI(UID="H1", db=db, autoload=True)
        security = SecurityAPI(Provider=provider, Ticker=ticker, db=db, autoload=True)
        spread = (SpreadType.Accurate, MISSING)
        commission = (CommissionType.Points, COMM)
        swap = (SwapType.Points, 0.0, 0.0)
        bt = BacktestingAPI(strategy=DDPGStrategyAPI, security=security, timeframe=timeframe, resolution=timeframe,
                            parameters=Parameter(node, str(MODEL / "Plot.yml")), start="2015-01-01", stop="2026-01-01",
                            account=("EUR", 10000.0, 30.0), spread=spread, commission=commission, swap=swap,
                            benchmark=None, report=False, export=False, plot=True, description=DESC)
        with bt:
            bt.run()
            pf = bt.portfolio
            eq = pf.Equity if pf is not None else None
            ib = pf.InitialBalance if pf is not None else None
            ret = (eq / ib - 1.0) * 100.0 if eq and ib else None
            print(f"LOADCHECK · Equity {eq} · Initial {ib} · AccountReturn {ret}%")
            sig = bt.strategy.Signals if bt.strategy is not None else []
            if sig:
                import statistics as st
                exps = [row[3] for row in sig]
                signs = [1 if e > 0 else -1 if e < 0 else 0 for e in exps]
                n = len(signs)
                longs = sum(1 for s in signs if s > 0); shorts = sum(1 for s in signs if s < 0); flats = n - longs - shorts
                segs = []; i = 0
                while i < n:
                    if signs[i] == 0: i += 1; continue
                    j = i
                    while j < n and signs[j] == signs[i]: j += 1
                    segs.append((signs[i], i, j - i)); i = j
                flips = sum(1 for k in range(1, len(segs)) if segs[k][0] != segs[k - 1][0])
                durs = [l for _, _, l in segs] or [0]
                print(f"EXPO · bars {n} · long {longs} ({100*longs/n:.1f}%) · short {shorts} ({100*shorts/n:.1f}%) · flat {flats} ({100*flats/n:.1f}%)")
                print(f"EXPO · directional-segments {len(segs)} · regime-flips {flips} · seg-dur mean {st.mean(durs):.0f} median {int(st.median(durs))} max {max(durs)} bars")
                for sgn, si, ln in sorted(segs, key=lambda x: -x[2])[:10]:
                    print(f"EXPO · {'LONG ' if sgn > 0 else 'SHORT'} {ln:>5} bars ({ln/24:.0f}d) · {sig[si][0].date()} -> {sig[min(si+ln-1, n-1)][0].date()}")
    print("PLOT_OK")
finally:
    DDPGStrategyAPI.Weights = None
