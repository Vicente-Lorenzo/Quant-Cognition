import os, sys, copy, math
from pathlib import Path

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"): stream.reconfigure(encoding="utf-8", errors="replace")
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
sys.path.insert(0, r"C:\Users\Admin\OneDrive\Documents\cAlgo")
os.chdir(r"C:\Users\Admin\OneDrive\Documents\cAlgo")

import yaml
from datetime import datetime
from Library.Database.Dataframe import np
from Library.Database.Postgres.Postgres import PostgresDatabaseAPI
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
NET = sys.argv[2] if len(sys.argv) > 2 else "64x32"
COMM = float(sys.argv[3]) if len(sys.argv) > 3 else 3.5
BALANCE = float(sys.argv[4]) if len(sys.argv) > 4 else 10000.0
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

CURVE = []
ORIGINAL = DDPGStrategyAPI._emit_

def _probe_(self, update, actions, raw=None):
    outcome = ORIGINAL(self, update, actions, raw)
    portfolio = update.Portfolio
    if portfolio is not None:
        delta = self._signed_volume_(actions)
        exposure = self._net_exposure_(update) + delta
        CURVE.append((update.Bar.Timestamp.DateTime, float(portfolio.Equity), float(exposure),
                      float(update.Bar.CloseTick.Bid.Price), abs(float(delta)),
                      float(raw) if raw is not None else float("nan")))
    return outcome

HandlerLoggingAPI(Class="Yearly", Subclass="Decomposition").set_verbose_level(VerboseLevel.Warning)
DDPGStrategyAPI.Weights = MODEL
DDPGStrategyAPI._emit_ = _probe_
try:
    with PostgresDatabaseAPI(database="Quant") as db:
        ticker = TickerAPI(UID="EURUSD", db=db, autoload=True)
        provider = ProviderAPI(UID="Spotware(cTrader)", db=db, autoload=True)
        timeframe = TimeframeAPI(UID="H1", db=db, autoload=True)
        security = SecurityAPI(Provider=provider, Ticker=ticker, db=db, autoload=True)
        bt = BacktestingAPI(strategy=DDPGStrategyAPI, security=security, timeframe=timeframe, resolution=timeframe,
                            parameters=Parameter(node, str(MODEL / "Yearly.yml")), start="2015-01-01", stop="2026-01-01",
                            account=("EUR", BALANCE, 30.0), spread=(SpreadType.Accurate, MISSING),
                            commission=(CommissionType.Points, COMM), swap=(SwapType.Points, 0.0, 0.0),
                            benchmark=None, report=False, export=False, plot=True, description="yearly")
        bt._plot_ = lambda *a, **k: None
        with bt:
            bt.run()
            final = float(bt.portfolio.Equity)
finally:
    DDPGStrategyAPI._emit_ = ORIGINAL
    DDPGStrategyAPI.Weights = None

DUMP = Path(os.environ.get("DECOMP_CSV", "curve.csv"))
NEWLINE = chr(10)
with DUMP.open("w", encoding="utf-8") as handle:
    handle.write("Timestamp,Equity,Exposure,Close,Delta,Raw" + NEWLINE)
    for row in CURVE:
        handle.write(f"{row[0].isoformat()},{row[1]:.6f},{row[2]:.6f},{row[3]:.6f},{row[4]:.6f},{row[5]:.6f}" + NEWLINE)
print(f"curve dumped -> {DUMP} ({len(CURVE)} rows)", flush=True)

stamps = [row[0] for row in CURVE]
equity = np.array([row[1] for row in CURVE])
exposure = np.array([row[2] for row in CURVE])
closes = np.array([row[3] for row in CURVE])
deltas = np.array([row[4] for row in CURVE])
years = np.array([s.year for s in stamps])

print(f"=== PER-YEAR DECOMPOSITION · {MODEL.name} · commission {COMM} pts · swap-free ===", flush=True)
print(f"  bars {len(CURVE)} · final equity {final:,.2f} · total {(final / BALANCE - 1.0) * 100.0:+.2f}%", flush=True)
print("", flush=True)
print(f"  {'year':<6}{'EURUSD':>9}{'return':>10}{'long%':>8}{'trades':>8}{'maxDD':>8}{'equity end':>13}", flush=True)
print(f"  {'-' * 62}", flush=True)

table = []
for y in sorted(set(int(v) for v in years)):
    sel = years == y
    if sel.sum() < 100: continue
    eq = equity[sel]; ex = exposure[sel]; cl = closes[sel]; dl = deltas[sel]
    opening = eq[0] if eq[0] > 0 else BALANCE
    ret = (eq[-1] / opening - 1.0) * 100.0
    move = (cl[-1] / cl[0] - 1.0) * 100.0
    active = int((ex != 0).sum())
    frac = 100.0 * float((ex > 0).sum()) / active if active else float("nan")
    peak = np.maximum.accumulate(eq)
    dd = float(((peak - eq) / np.where(peak > 0, peak, 1.0)).max() * 100.0)
    trades = int((dl > 0).sum())
    table.append((y, move, ret, frac, trades, dd, eq[-1]))
    print(f"  {y:<6}{move:>+8.2f}%{ret:>+9.2f}%{frac:>7.1f}%{trades:>8}{dd:>7.1f}%{eq[-1]:>13,.0f}", flush=True)

rets = [row[2] for row in table]
positive = sum(1 for r in rets if r > 0)
print(f"  {'-' * 62}", flush=True)
print(f"  positive years {positive}/{len(rets)} · median {sorted(rets)[len(rets) // 2]:+.2f}% · mean {sum(rets) / len(rets):+.2f}%", flush=True)
print("", flush=True)

print("=== DROP-ONE-YEAR JACKKNIFE (is the result one lucky year?) ===", flush=True)
compound = lambda values: (math.prod(1.0 + v / 100.0 for v in values) - 1.0) * 100.0
print(f"  compounded all years     : {compound(rets):+.2f}%", flush=True)
worst = None
for index, row in enumerate(table):
    without = compound([r for j, r in enumerate(rets) if j != index])
    if worst is None or without < worst[1]: worst = (row[0], without)
    print(f"  without {row[0]}             : {without:+.2f}%   (removed year contributed {rets[index]:+.2f}%)", flush=True)
print(f"  ⇒ worst case, dropping {worst[0]}: {worst[1]:+.2f}%", flush=True)
print(f"  ⇒ survives dropping ANY single year: {'YES' if worst[1] > 0 else 'NO'}", flush=True)
