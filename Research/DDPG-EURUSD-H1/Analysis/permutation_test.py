import os, sys, copy, math
from pathlib import Path

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"): stream.reconfigure(encoding="utf-8", errors="replace")
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
sys.path.insert(0, r"C:\Users\Admin\OneDrive\Documents\cAlgo")
os.chdir(r"C:\Users\Admin\OneDrive\Documents\cAlgo")

import yaml
from datetime import datetime
from Library.Database.Dataframe import np, pd
from Library.Database.Postgres.Postgres import PostgresDatabaseAPI
from Library.Logging import LoggingAPI, VerboseLevel
from Library.Market.Market import MarketAPI
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
COMM = float(sys.argv[3]) if len(sys.argv) > 3 else 3.5
DRAWS = int(sys.argv[4]) if len(sys.argv) > 4 else 2000
H1, H2 = (int(x) for x in NET.split("x"))

YML = Path("Library/Parameter/Spotware(cTrader)/Forex(Major)/EURUSD/Hour/Learning.yml")
node = copy.deepcopy(yaml.safe_load(YML.read_text(encoding="utf-8"))["DDPG"])
mm = node["MoneyManagement"]; mm["RiskPercentage"] = [1.0]; mm["ATRScale"] = [1.5]
sm = node["SignalManagement"]
sm["HiddenShape1"] = [H1]; sm["HiddenShape2"] = [H2]; sm["ObservationWindow"] = [1]
sm["DirectionalEntryThreshold"] = [-0.0, 0.0]; sm["DirectionalExitThreshold"] = [-0.0, 0.0]
sm["VolumeEntryThreshold"] = None; sm["VolumeExitThreshold"] = None
sm.pop("Weights", None)
sm["AccountFeatures"] = [False]
sm["DecisionSchedule"] = ["D1"]
sm["RebalanceThreshold"] = [0.20]
tm = node["TechnicalManagement"]
tm["MOMRegime"] = ["ROC", 1440]; tm["MOMEpoch"] = ["ROC", 2880]
tm["MARegime"] = ["SMA", 1440]; tm["MAEpoch"] = ["SMA", 2880]
tm["MACycle"] = ["SMA", 4320]; tm["MAEra"] = ["SMA", 5040]
node["PortfolioManagement"] = {"PositionMode": ["Netting"]}

LoggingAPI().set_level(VerboseLevel.Warning)
DDPGStrategyAPI.Weights = MODEL
try:
    with PostgresDatabaseAPI(database="Quant") as db:
        ticker = TickerAPI(UID="EURUSD", db=db, autoload=True)
        provider = ProviderAPI(UID="Spotware(cTrader)", db=db, autoload=True)
        timeframe = TimeframeAPI(UID="H1", db=db, autoload=True)
        security = SecurityAPI(Provider=provider, Ticker=ticker, db=db, autoload=True)
        bt = BacktestingAPI(strategy=DDPGStrategyAPI, security=security, timeframe=timeframe, resolution=timeframe,
                            parameters=Parameter(node, str(MODEL / "Perm.yml")), start="2015-01-01", stop="2026-01-01",
                            account=("EUR", 10000.0, 30.0), spread=(SpreadType.Accurate, MISSING),
                            commission=(CommissionType.Points, COMM), swap=(SwapType.Points, 0.0, 0.0),
                            benchmark=None, report=False, export=False, plot=True, description="permutation")
        bt._plot_ = lambda *a, **k: None
        with bt:
            bt.run()
            signals = list(bt.strategy.Signals)
        frame = MarketAPI.pull_bars(db, security.UID, timeframe.UID, start=datetime(2015, 1, 1), stop=datetime(2026, 1, 1)).to_pandas()
finally:
    DDPGStrategyAPI.Weights = None

price = {ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else ts: float(px) for ts, px in zip(frame["Timestamp"], frame["CloseTick.Bid"])}
rows = [(row[0], float(row[3])) for row in signals if row[0] in price]
stamps = [r[0] for r in rows]
exposure = np.array([r[1] for r in rows])
years = np.array([s.year for s in stamps])
closes = np.array([price[s] for s in stamps])

moves = {}
for y in np.unique(years):
    sel = years == y
    if sel.sum() > 100: moves[int(y)] = (closes[sel][-1] / closes[sel][0] - 1.0) * 100.0

def regime(expo):
    weighted = total = 0.0
    for y, move in moves.items():
        sel = years == y
        ss = expo[sel]
        active = int((ss != 0).sum())
        if active < 100: continue
        frac = float((ss > 0).sum()) / active
        weighted += (frac if move > 0 else 1.0 - frac) * abs(move); total += abs(move)
    return 100.0 * weighted / total if total else 0.0

actual = regime(exposure)
n = len(exposure)
rng = np.random.default_rng(12345)
null = np.empty(DRAWS)
for i in range(DRAWS):
    null[i] = regime(np.roll(exposure, int(rng.integers(1, n))))

mean, sd = float(null.mean()), float(null.std())
above = int((null >= actual).sum())
pvalue = (above + 1) / (DRAWS + 1)
z = (actual - mean) / sd if sd > 0 else float("nan")
print(f"=== PERMUTATION TEST · regime score · {DRAWS} circular rotations ===", flush=True)
print(f"  rotation preserves the policy's own autocorrelation and hold structure EXACTLY,", flush=True)
print(f"  and destroys only its alignment with the market ⇒ a matched null.", flush=True)
print(f"  actual regime score      : {actual:.2f}%", flush=True)
print(f"  null mean ± sd           : {mean:.2f}% ± {sd:.2f}", flush=True)
print(f"  null 5th / 50th / 95th   : {np.percentile(null,5):.2f}% / {np.percentile(null,50):.2f}% / {np.percentile(null,95):.2f}%", flush=True)
print(f"  null max over {DRAWS} draws : {null.max():.2f}%", flush=True)
print(f"  z-score                  : {z:+.2f}", flush=True)
print(f"  one-sided p-value        : {pvalue:.5f}  ({above} of {DRAWS} rotations matched or beat it)", flush=True)
