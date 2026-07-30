import os, sys, copy, json, time, shutil, traceback
from pathlib import Path

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"): stream.reconfigure(encoding="utf-8", errors="replace")
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
sys.path.insert(0, r"C:\Users\Admin\OneDrive\Documents\cAlgo")
os.chdir(r"C:\Users\Admin\OneDrive\Documents\cAlgo")

import torch
torch.set_num_threads(int(os.environ.get("SWEEP_THREADS", "6")))
import yaml
from Library.Database.Postgres.Postgres import PostgresDatabaseAPI
from Library.Logging import LoggingAPI, VerboseLevel
from Library.Parameter import Parameter
from Library.Strategy.Hybrid.DDPG import DDPGStrategyAPI
from Library.System.Learning import LearningAPI
from Library.Universe.Provider import ProviderAPI
from Library.Universe.Ticker import TickerAPI
from Library.Universe.Timeframe import TimeframeAPI
from Library.Universe.Security import SecurityAPI
from Library.Universe.Contract import CommissionType, SpreadType, SwapType
from Library.Utility.Typing import MISSING

TICKER = "EURUSD"
YML = Path(f"Library/Parameter/Spotware(cTrader)/Forex(Major)/{TICKER}/Hour/Learning.yml")
BASE = yaml.safe_load(YML.read_text(encoding="utf-8"))["DDPG"]
HOUR = YML.parent

# --- FROZEN (not swept) ---
REWARD = os.environ.get("SWEEP_REWARD", "DifferentialSortino")
NEUTRALIZE = os.environ.get("SWEEP_NEUTRALIZE", "1") == "1"
REWARD_CLIP = 1.0
FITNESS = os.environ.get("SWEEP_FITNESS", "CalmarRatio")
ATR_SCALE = float(os.environ.get("SWEEP_ATR", "1.5"))
RISK_PCT = float(os.environ.get("SWEEP_RISK", "1.0"))
GAMMA = float(os.environ.get("SWEEP_GAMMA", "0.998"))
GRAD_CLIP = 1.0
OBS_WINDOW = int(os.environ.get("SWEEP_OBS_WINDOW", "1"))
EPISODES = int(os.environ.get("SWEEP_EPISODES", "20"))
PATIENCE = int(os.environ.get("SWEEP_PATIENCE", "5"))
SEEDS = int(os.environ.get("SWEEP_SEEDS", "4"))
WORKERS = int(os.environ.get("SWEEP_WORKERS", "4"))
TRAINING = 0
VALIDATION = 12
TESTING = 12
ROLLING = False
CONTINUOUS = False
START, STOP = "2015-01-01", "2026-01-01"
FRICTIONLESS = os.environ.get("SWEEP_FRICTIONLESS", "1") == "1"
MIRROR = os.environ.get("SWEEP_MIRROR", "0") == "1"

# --- SWEPT ---
NETS = [(64, 32), (64, 64)]
LAMBDAS = [0.001, 0.01]
WARMUPS = [3000]
THRESHOLDS = [0.1, 0.2]

def costs():
    if FRICTIONLESS:
        return (SpreadType.Accurate, MISSING), (CommissionType.Points, 0.0), (SwapType.Points, 0.0, 0.0)
    return (SpreadType.Accurate, MISSING), (CommissionType.Points, float(os.environ.get("SWEEP_COMMISSION", "0.2"))), (SwapType.Points, 0.0, 0.0)

def build(h1, h2, lam, warmup, threshold):
    node = copy.deepcopy(BASE)
    mm = node["MoneyManagement"]
    mm["RiskPercentage"] = [RISK_PCT]
    mm["ATRScale"] = [ATR_SCALE]
    sm = node["SignalManagement"]
    sm["HiddenShape1"] = [h1]
    sm["HiddenShape2"] = [h2]
    sm["ObservationWindow"] = [OBS_WINDOW]
    sm["DiscountFactor"] = [GAMMA]
    sm["GradientClip"] = [GRAD_CLIP]
    sm["ActorRegularization"] = [lam]
    sm["WarmupSteps"] = [warmup]
    sm["NeutralizeReward"] = [NEUTRALIZE]
    sm["NeutralizeScale"] = [float(os.environ.get("SWEEP_NEUTRALIZE_SCALE", "1.0"))]
    sm["RewardClip"] = [REWARD_CLIP]
    reward_scale = float(os.environ.get("SWEEP_REWARD_SCALE", "1"))
    if reward_scale != 1.0: sm["RewardScale"] = [reward_scale]
    band = [-threshold, threshold]
    sm["DirectionalEntryThreshold"] = band
    sm["DirectionalExitThreshold"] = band
    sm["VolumeEntryThreshold"] = None
    sm["VolumeExitThreshold"] = None
    turnover = float(os.environ.get("SWEEP_TURNOVER", "0"))
    if turnover > 0.0: sm["TurnoverCost"] = [turnover]
    smoothing = float(os.environ.get("SWEEP_SMOOTHING", "0"))
    if smoothing > 0.0: sm["SignalSmoothing"] = [smoothing]
    interval = int(os.environ.get("SWEEP_DECISION_INTERVAL", "1"))
    if interval > 1: sm["DecisionInterval"] = [interval]
    sched = os.environ.get("SWEEP_DECISION_SCHEDULE")
    if sched: sm["DecisionSchedule"] = [sched]
    if os.environ.get("SWEEP_ACCOUNT_FEATURES", "1") == "0": sm["AccountFeatures"] = [False]
    sm.pop("Weights", None)
    slow = os.environ.get("SWEEP_SLOW_FEATURES", "0")
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
    return node

def label(h1, h2, lam, warmup, threshold):
    reg = "ddpg" if lam == 0.0 else f"rddpg{lam:g}"
    thr = "thctl" if threshold == 0.0 else f"th{threshold:g}"
    mir = " mir" if MIRROR else ""
    return f"n{h1}x{h2} {reg} wu{warmup} {thr}{mir}"

def main():
    LoggingAPI(Class="Sweep", Subclass="Campaign").set_level(VerboseLevel[os.environ.get("SWEEP_VERBOSE", "Warning")])
    spread, commission, swap = costs()
    wroot = os.environ.get("SWEEP_WEIGHTS_ROOT")
    if wroot:
        DDPGStrategyAPI._DEFAULT_WEIGHTS_ = Path(wroot)
        export_parent = Path(wroot)
        export_parent.mkdir(parents=True, exist_ok=True)
    else:
        export_parent = HOUR
    yaml_path = str(export_parent / "Learning.yml")
    worker_threads = int(os.environ.get("SWEEP_WORKER_THREADS", "1"))
    plot = os.environ.get("SWEEP_PLOT", "1") == "1"
    arm_net = os.environ.get("SWEEP_NET")
    if arm_net:
        ah1, ah2 = (int(x) for x in arm_net.split("x"))
        configs = [(ah1, ah2, float(os.environ.get("SWEEP_LAMBDA", "0.001")), int(os.environ.get("SWEEP_WARMUP", "3000")), float(os.environ.get("SWEEP_THRESHOLD", "0.1")))]
    else:
        configs = [(h1, h2, lam, wu, thr) for (h1, h2) in NETS for lam in LAMBDAS for wu in WARMUPS for thr in THRESHOLDS]
    indices = os.environ.get("SWEEP_INDICES")
    if indices:
        configs = [configs[int(i)] for i in indices.split(",")]
    only = os.environ.get("SWEEP_ONLY")
    if only:
        configs = [configs[int(only)]]
    RESULTS = Path(os.environ.get("SWEEP_RESULTS", str(HOUR / "_campaign_H1_results.json")))
    results = json.loads(RESULTS.read_text(encoding="utf-8")) if RESULTS.exists() and os.environ.get("SWEEP_RESUME") else []
    done = {r["tag"] for r in results if "error" not in r}
    friction = "frictionless" if FRICTIONLESS else "realistic"
    neu = "neu" if NEUTRALIZE else "raw"
    mir = "mir" if MIRROR else "nomir"
    print(f"[CAMPAIGN H1] {len(configs)} configs · {friction} · reward {REWARD}+{neu} · {mir} · balance {os.environ.get('SWEEP_BALANCE','0')} ratio {os.environ.get('SWEEP_RATIO','0')} · fitness {FITNESS} · gamma {GAMMA} · atr {ATR_SCALE} · risk {RISK_PCT} · seeds {SEEDS} · episodes {EPISODES} · patience {PATIENCE}", flush=True)
    with PostgresDatabaseAPI(database="Quant") as db:
        ticker = TickerAPI(UID=TICKER, db=db, autoload=True)
        provider = ProviderAPI(UID="Spotware(cTrader)", db=db, autoload=True)
        timeframe = TimeframeAPI(UID="H1", db=db, autoload=True)
        security = SecurityAPI(Provider=provider, Ticker=ticker, db=db, autoload=True)
        for (h1, h2, lam, wu, thr) in configs:
            tag = label(h1, h2, lam, wu, thr)
            if tag in done:
                print(f"[SKIP] {tag} (already done)", flush=True)
                continue
            try:
                node = build(h1, h2, lam, wu, thr)
                thr_label = "control [-0,0]" if thr == 0.0 else f"±{thr:g}"
                desc = (f"Learning · DDPGStrategyAPI · {TICKER} H1 · net {h1}x{h2} · λ {lam:g} · warmup {wu} · mirror {'on' if MIRROR else 'off'} · threshold {thr_label} · "
                        f"reward {REWARD}{'+Neutralize' if NEUTRALIZE else ' raw'} (clip {REWARD_CLIP}) · fitness {FITNESS} · γ {GAMMA} · gradClip {GRAD_CLIP} · "
                        f"ATRScale {ATR_SCALE} · RiskPct {RISK_PCT} · episodes {EPISODES} · patience {PATIENCE} · seeds {SEEDS} · {friction}")
                before = set(p.name for p in export_parent.glob("DDPG *"))
                t0 = time.time()
                learner = LearningAPI(strategy=DDPGStrategyAPI, security=security, timeframe=timeframe,
                                      parameters=Parameter(node, yaml_path), start=START, stop=STOP,
                                      account=("EUR", 10000.0, 30.0), spread=spread, commission=commission, swap=swap,
                                      reward=REWARD, episodes=EPISODES, epochs=1, train_frequency=1, gradient_steps=1,
                                      training=TRAINING, validation=VALIDATION, testing=TESTING, rolling=ROLLING, continuous=CONTINUOUS,
                                      fitness=FITNESS, patience=PATIENCE, activity=int(os.environ.get("SWEEP_ACTIVITY", "10")), balance=int(os.environ.get("SWEEP_BALANCE", "0")), ratio=float(os.environ.get("SWEEP_RATIO", "0")), mirror=MIRROR, mirror_ratio=float(os.environ.get("SWEEP_MIRROR_RATIO", "0.5")), final=os.environ.get("SWEEP_FINAL", "0") == "1",
                                      seed=None, seeds=SEEDS, workers=WORKERS, threads=worker_threads,
                                      benchmark=(os.environ.get("SWEEP_BENCHMARK") or None),
                                      report=False, export=False, plot=plot, description=desc)
                with learner:
                    learner.run()
                dt = time.time() - t0
                manifest_path = learner._weights_ / "DDPGStrategyAPI Manifest.json"
                manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
                after = set(p.name for p in export_parent.glob("DDPG *"))
                new = sorted(after - before)
                export = None
                if new:
                    src = export_parent / new[-1]
                    dst = HOUR / f"{new[-1]} [{tag}]"
                    if dst.exists(): dst = HOUR / f"{new[-1]} [{tag}] {os.getpid()}"
                    shutil.move(str(src), str(dst))
                    export = dst
                res = manifest.get("Results", [])
                test_returns = [r.get("TestReturn") for r in res if r.get("TestReturn") is not None]
                fr = manifest.get("FullRange", {}) or {}
                record = {
                    "tag": tag, "net": f"{h1}x{h2}", "lambda": lam, "warmup": wu, "threshold": thr, "friction": friction,
                    "obs_shape": manifest.get("ObservationShape"), "seconds": round(dt, 1),
                    "test_return_mean": (sum(test_returns) / len(test_returns)) if test_returns else None,
                    "test_return_max": max(test_returns) if test_returns else None,
                    "test_return_min": min(test_returns) if test_returns else None,
                    "test_returns": test_returns,
                    "best_validation": manifest.get("Best"),
                    "fr_net": fr.get("NetReturn"), "fr_account": fr.get("AccountReturn"), "fr_ann": fr.get("AnnualizedReturn"),
                    "fr_sharpe": fr.get("Sharpe"), "fr_sortino": fr.get("Sortino"),
                    "fr_calmar": fr.get("Calmar"), "fr_maxdd": fr.get("MaxDrawdown"),
                    "fr_trades": fr.get("Trades"), "fr_buys": fr.get("BuyTrades"), "fr_sells": fr.get("SellTrades"),
                    "fr_longbars": fr.get("LongBars"), "fr_shortbars": fr.get("ShortBars"),
                    "export": str(export) if export else None,
                }
            except Exception as exc:
                record = {"tag": tag, "net": f"{h1}x{h2}", "lambda": lam, "warmup": wu, "threshold": thr, "error": repr(exc), "trace": traceback.format_exc()}
                print(f"[FAIL] {tag} · {exc}", flush=True)
            results.append(record)
            RESULTS.write_text(json.dumps(results, indent=2), encoding="utf-8")
            if "error" not in record:
                b, s = int(record["fr_buys"] or 0), int(record["fr_sells"] or 0)
                lb, sb = int(record["fr_longbars"] or 0), int(record["fr_shortbars"] or 0)
                xratio = min(lb, sb) / max(lb, sb) if max(lb, sb) else 0.0
                acct = record["fr_account"]
                goal = "  ★GOAL(expo-2-sided+positive)" if acct is not None and acct > 0 and xratio >= 0.3 and min(lb, sb) >= 300 else ""
                print(f"[DONE] {tag} · {record['seconds']}s · acctRet {acct}% · B/S {b}/{s} · expoL/S {lb}/{sb} (xr {xratio:.2f}) · maxDD {record['fr_maxdd']}% · testMin {record['test_return_min']}{goal}", flush=True)
    ok = [r for r in results if "error" not in r and r.get("fr_account") is not None]
    def two_sided(r):
        lb, sb = int(r.get("fr_longbars") or 0), int(r.get("fr_shortbars") or 0)
        return min(lb, sb) >= 300 and (min(lb, sb) / max(lb, sb) if max(lb, sb) else 0.0) >= 0.3
    ok.sort(key=lambda r: (two_sided(r) and (r["fr_account"] or -1e9) > 0, r["fr_account"] if r["fr_account"] is not None else -1e9), reverse=True)
    print(f"\n=== CAMPAIGN RANKING (goal: EXPOSURE-two-sided + positive AccountReturn > EURUSD b&h ~-7%) ===", flush=True)
    for r in ok:
        lb, sb = int(r.get("fr_longbars") or 0), int(r.get("fr_shortbars") or 0)
        xr = min(lb, sb) / max(lb, sb) if max(lb, sb) else 0.0
        meets = "★" if two_sided(r) and (r["fr_account"] or -1) > 0 else " "
        print(f"  {meets} {r['tag']:>26} · acctRet {r['fr_account']}% · expoL/S {lb}/{sb} (xr {xr:.2f}) · maxDD {r['fr_maxdd']}% · testMin {r['test_return_min']}", flush=True)
    print(f"\n[CAMPAIGN H1] complete · results {RESULTS}", flush=True)

if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    main()
