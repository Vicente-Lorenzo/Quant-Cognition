import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from Library.Strategy.Hybrid.DDPG import DDPGStrategyAPI
from Library.Utility.IO import mkdir, write_yaml
from Library.Utility.Path import inspect_persistent

NAME = "DDPG 2026-09"
PAIRS = ("AUDUSD", "EURUSD", "GBPUSD", "NZDUSD", "USDCAD", "USDCHF", "USDJPY")
WINDOW = ("2015-01-01", "2026-01-01")
ACCOUNT = ["--account-asset", "USD", "--account-balance", "10000", "--account-leverage", "30"]
FRICTIONLESS = ["--spread-type", "Accurate", "--commission-type", "Lots", "--commission-value", "0", "--swap-type", "Points", "--swap-buy", "0", "--swap-sell", "0"]
FRICTIONS = ["--spread-type", "Accurate", "--commission-type", "Lots", "--commission-value", "3.5", "--swap-type", "Points", "--swap-buy", "0", "--swap-sell", "0"]
SPLIT = ["--training", "36", "--validation", "12", "--testing", "12", "--rolling", "--continuous"]
PROTOCOL = ["--episodes", "20", "--threads", "1", "--selection", "Best", "--election", "Last", "--fitness", "CalmarRatio", "--mirror", "--mirror-ratio", "0.5", "--activity", "10", "--balance", "300", "--ratio", "0.30"]
ARMS = {"A": (FRICTIONLESS, 0.0), "B": (FRICTIONS, 0.2)}

def root() -> Path:
    return inspect_persistent("Campaigns", NAME)

def folder(pair: str, arm: str, seed: int, seeds: int) -> Path:
    return root() / pair / f"Arm {arm}" / f"Seeds {seed}-{seed + seeds - 1}"

def parameters(arm: str) -> Path:
    data = DDPGStrategyAPI.defaults("Learning")
    data["SignalManagement"]["RebalanceThreshold"] = [ARMS[arm][1]]
    path = root() / f"Learning {arm}.yml"
    mkdir(path.parent, safe=False)
    write_yaml(path, data, safe=False)
    return path

def learning(pair: str, arm: str, seed: int, seeds: int, workers: int) -> list[str]:
    return ["Learning", "--strategy", "DDPG", "--ticker", pair, "--timeframe", "Hour", "--start", WINDOW[0], "--stop", WINDOW[1], *ACCOUNT, *ARMS[arm][0], *SPLIT, *PROTOCOL,
            "--seed", str(seed), "--seeds", str(seeds), "--workers", str(workers), "--parameters", str(parameters(arm)), "--export", "--console", "Warning", "--file", "Info",
            "--description", f"{NAME} · {pair} · Arm {arm} · Seeds {seed}-{seed + seeds - 1}", "--run", str(folder(pair, arm, seed, seeds))]