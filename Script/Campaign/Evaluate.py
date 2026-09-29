import sys
import time
from pathlib import Path
from argparse import ArgumentParser
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import psutil

from Library.Database.Dataframe import np, pl
from Library.Logging import LoggingAPI, VerboseLevel
from Library.Statistic.Behaviour import exposure_beta, null, persistence, sidedness
from Library.Statistic.Curve import CurveAPI
from Library.Strategy.Hybrid.DDPG import DDPGStrategyAPI
from Library.System.Backtesting import BacktestingAPI
from Library.System.Main import SystemCommandAPI
from Library.Utility.IO import mkdir, read_json, write_yaml
from Script.Campaign.Campaign import ACCOUNT, FRICTIONS, PAIRS, root

GIGABYTE = 2 ** 30
FOLDS = {f"Fold {index}": (f"{2017 + index}-01-01", f"{2017 + index}-12-31") for index in range(1, 8)}
WINDOWS = {**FOLDS, "Test": ("2025-01-01", "2025-12-31"), "Full": ("2015-01-01", "2025-12-31")}
MONEY, SAFETY, BEHAVIOUR = ("VAnnual", "VCalmar", "VSterling"), ("VSharpe", "VSortino", "-VMaxDD"), ("Weaker", "Edge", "MeanHoldDays", "-AbsBeta")

def _jobs_(pair: str) -> list[Path]:
    return sorted(job for job in (root() / pair).glob("Arm */Seeds *") if (read_json(job / "Job.json") or {}).get("Status") == "Completed")

def _seeds_(job: Path) -> list[int]:
    return sorted(int(folder.name.split()[1]) for folder in (job / "Output" / "Weights").glob("Seed *"))

def _target_(job: Path, seed: int, label: str) -> Path:
    return job / "Evaluation" / f"Seed {seed}" / label

def _weights_(job: Path, seed: int, label: str) -> Path:
    return job / "Output" / "Weights" / f"Seed {seed}" / (label if label in FOLDS else "Fold 7")

def _backtest_(task: tuple) -> tuple:
    pair, job, seed, label = task
    target = _target_(Path(job), seed, label)
    if (target / "Output" / "Export" / "prices.csv").is_file(): return task, "Reused"
    data = DDPGStrategyAPI.defaults("Backtesting")
    data["SignalManagement"]["Weights"] = [str(_weights_(Path(job), seed, label))]
    mkdir(target, safe=False)
    write_yaml(target / "Weights.yml", data, safe=False)
    start, stop = WINDOWS[label]
    code = SystemCommandAPI().main(["Backtesting", "--strategy", "DDPG", "--ticker", pair, "--timeframe", "Hour", "--resolution", "H1", "--start", start, "--stop", stop, *ACCOUNT, *FRICTIONS,
                                    "--parameters", str(target / "Weights.yml"), "--export", "--console", "Error", "--file", "Warning", "--run", str(target)])
    return task, "Completed" if code == 0 else "Failed"

def _window_(tasks: list) -> list:
    BacktestingAPI._PRELOAD_CACHE_.clear()
    BacktestingAPI._TAPE_CACHE_.clear()
    return [_backtest_(task) for task in tasks]

def _frame_(target: Path) -> pl.DataFrame:
    export = target / "Output" / "Export"
    prices = pl.read_csv(export / "prices.csv", try_parse_dates=True)
    equity = pl.read_csv(export / "equity.csv", try_parse_dates=True)
    signals = pl.read_csv(export / "signals.csv", try_parse_dates=True).select("Timestamp", "Exposure") if (export / "signals.csv").is_file() else pl.DataFrame({"Timestamp": prices["Timestamp"], "Exposure": 0.0})
    frame = prices.join(equity, on="Timestamp", how="left").join(signals, on="Timestamp", how="left")
    return frame.with_columns(pl.col("Equity").fill_null(strategy="forward").fill_null(strategy="backward"), pl.col("Exposure").fill_null(strategy="forward").fill_null(0.0))

def _curve_(stamps: list, values: list, prefix: str) -> dict:
    curve = CurveAPI()
    for stamp, value in zip(stamps, values):
        curve.record(stamp, value)
        curve.observe(value)
    return {f"{prefix}Return": curve.Return, f"{prefix}Annual": curve.AnnualizedReturn, f"{prefix}MaxDD": curve.MaxDrawdown, f"{prefix}Sharpe": curve.SharpeRatioAnnualized,
            f"{prefix}Sortino": curve.SortinoRatioAnnualized, f"{prefix}Calmar": curve.CalmarRatioAnnualized, f"{prefix}Sterling": curve.SterlingRatioAnnualized}

def _metrics_(job: Path, seed: int) -> dict:
    record, frames, factor, model, market = {"Pair": job.parent.parent.name, "Arm": job.parent.name.split()[1], "Job": job.name, "Seed": seed}, [], 1.0, [], []
    for label in FOLDS:
        frame = _frame_(_target_(job, seed, label))
        equity, close = frame["Equity"].to_numpy(), frame["Close"].to_numpy()
        year, gain, move = label.replace("Fold ", "F"), equity[-1] / equity[0] - 1.0, close[-1] / close[0] - 1.0
        record[year], record[f"P{year[1:]}"] = gain, move
        model.append(gain)
        market.append(move)
        frames.append(frame.with_columns((pl.col("Equity") / equity[0] * factor).alias("Stitched")))
        factor *= 1.0 + gain
    stitched = pl.concat(frames)
    record.update(_curve_(stitched["Timestamp"].to_list(), stitched["Stitched"].to_list(), "V"))
    record["VPair"] = float(np.prod(1.0 + np.array(market)) - 1.0)
    record["VBeats"] = record["VReturn"] > record["VPair"]
    exposure, closes, years = stitched["Exposure"].to_numpy(), stitched["Close"].to_numpy(), stitched["Timestamp"].dt.year().to_numpy()
    record["Active"], record["Long"], record["Weaker"] = sidedness(exposure)
    record.update(persistence(exposure))
    regime = null(exposure, closes, years, seed=seed)
    record.update({"Regime": regime["Regime"], "NullMedian": regime.get("NullMedian"), "P": regime["P"]})
    record["Edge"] = regime["Regime"] - regime["NullMedian"] if regime["Regime"] is not None and regime.get("NullMedian") is not None else None
    record["Beta"], record["Alpha"] = exposure_beta(np.array(model), np.array(market))
    record["AbsBeta"] = abs(record["Beta"]) if record["Beta"] is not None else None
    test = _frame_(_target_(job, seed, "Test"))
    record.update(_curve_(test["Timestamp"].to_list(), test["Equity"].to_list(), "T"))
    closes = test["Close"].to_numpy()
    record["TPair"] = closes[-1] / closes[0] - 1.0
    record["TBeats"] = record["TReturn"] > record["TPair"]
    record["TLong"] = sidedness(test["Exposure"].to_numpy())[1]
    record["Gates"] = int(record["VReturn"] > 0.0) + int(record["VBeats"]) + int(record["Weaker"] >= 0.10) + int(record["MeanHoldDays"] >= 1.0) + int(record["Edge"] is not None and record["Edge"] > 0.0)
    return record

def _composite_(frame: pl.DataFrame) -> pl.DataFrame:
    ranks = []
    for group in (MONEY, SAFETY, BEHAVIOUR):
        columns = []
        for metric in group:
            name, sign = (metric[1:], -1.0) if metric.startswith("-") else (metric, 1.0)
            values = frame[name].fill_null(-np.inf if sign > 0 else np.inf).to_numpy() * sign
            columns.append(np.array([100.0 * np.count_nonzero(values < value) / max(values.size - 1, 1) for value in values]))
        ranks.append(np.mean(columns, axis=0))
    return frame.with_columns(pl.Series("Composite", np.mean(ranks, axis=0)))

def _summary_(frame: pl.DataFrame) -> dict:
    best = frame.row(0, named=True)
    job = root() / best["Pair"] / f"Arm {best['Arm']}" / best["Job"]
    _window_([(best["Pair"], str(job), best["Seed"], "Full")])
    full = _frame_(_target_(job, best["Seed"], "Full"))
    closes = full["Close"].to_numpy()
    arms = {arm: frame.filter(pl.col("Arm") == arm) for arm in sorted(frame["Arm"].unique().to_list())}
    counts = " · ".join(f"{arm} {group.filter(pl.col('Gates') == 5).height}/{group.height}" for arm, group in arms.items())
    return {**best, "Status": "Elected" if best["Gates"] == 5 else "Provisional", "Passing": counts, **_curve_(full["Timestamp"].to_list(), full["Equity"].to_list(), "A"), "APair": closes[-1] / closes[0] - 1.0}

def main() -> int:
    parser = ArgumentParser()
    parser.add_argument("--pairs", nargs="+", default=list(PAIRS), choices=PAIRS)
    parser.add_argument("--processes", type=int, default=2)
    parser.add_argument("--floor", type=float, default=8.0)
    args = parser.parse_args()
    log = LoggingAPI("Campaign")
    log.console.set_level(VerboseLevel.Info)
    log.file.set_level(VerboseLevel.Info)
    with log:
        for pair in args.pairs:
            jobs = _jobs_(pair)
            if not jobs: continue
            groups = [[(pair, str(job), seed, label) for job in jobs for seed in _seeds_(job)] for label in (*FOLDS, "Test")]
            began, failed = time.perf_counter(), 0
            with ProcessPoolExecutor(max_workers=args.processes) as pool:
                pending = []
                for group in groups:
                    while psutil.virtual_memory().available / GIGABYTE < args.floor: time.sleep(30)
                    pending.append(pool.submit(_window_, group))
                for future in pending: failed += sum(1 for _, status in future.result() if status == "Failed")
            records = []
            for job in jobs:
                for seed in _seeds_(job):
                    try: records.append(_metrics_(job, seed))
                    except Exception as error: log.warning(lambda job=job, seed=seed, error=error: f"Evaluation Campaign: Skipped · {job.parent.name} Seed {seed} · {error}")
            frame = _composite_(pl.DataFrame(records, infer_schema_length=None)).sort(["Gates", "Composite"], descending=True)
            mkdir(root() / "Evaluation", safe=False)
            frame.write_csv(root() / "Evaluation" / f"{pair}.csv")
            summary = root() / "Summary.csv"
            rows = pl.read_csv(summary).filter(pl.col("Pair") != pair).to_dicts() if summary.is_file() else []
            pl.DataFrame([*rows, _summary_(frame)], infer_schema_length=None).sort("Pair").write_csv(summary)
            log.info(lambda pair=pair, frame=frame, failed=failed, began=began: f"Evaluation Campaign: Completed · {pair} · {frame.height} Seeds · {frame.filter(pl.col('Gates') == 5).height} Pass · {failed} Failed · {time.perf_counter() - began:.0f}s")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())