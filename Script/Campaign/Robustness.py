import sys
from pathlib import Path
from argparse import ArgumentParser

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from Library.Database.Dataframe import pl
from Library.Logging import LoggingAPI, VerboseLevel
from Library.Strategy.Hybrid.DDPG import DDPGStrategyAPI
from Library.System.Backtesting import BacktestingAPI
from Library.System.Main import SystemCommandAPI
from Library.Utility.IO import mkdir, write_yaml
from Script.Campaign.Campaign import PAIRS, root
from Script.Campaign.Evaluate import WINDOWS, _curve_, _frame_

BALANCES = (9900, 10000, 10050, 10100, 10200, 2500, 5000, 20000, 50000, 100000)
COMMISSIONS = (0.0, 7.0)

def _variants_() -> list[tuple[str, list[str]]]:
    spread, swap = ["--spread-type", "Accurate"], ["--swap-type", "Points", "--swap-buy", "0", "--swap-sell", "0"]
    variants = [(f"Balance {balance}", ["--account-balance", str(balance), *spread, "--commission-type", "Lots", "--commission-value", "3.5", *swap]) for balance in BALANCES]
    variants += [(f"Commission {commission:g}", ["--account-balance", "10000", *spread, "--commission-type", "Lots", "--commission-value", str(commission), *swap]) for commission in COMMISSIONS]
    variants.append(("Swap Broker", ["--account-balance", "10000", *spread, "--commission-type", "Lots", "--commission-value", "3.5", "--swap-type", "Accurate"]))
    return variants

def main() -> int:
    parser = ArgumentParser()
    parser.add_argument("--pairs", nargs="+", default=list(PAIRS), choices=PAIRS)
    args = parser.parse_args()
    log = LoggingAPI("Campaign")
    log.console.set_level(VerboseLevel.Info)
    log.file.set_level(VerboseLevel.Info)
    summary = pl.read_csv(root() / "Summary.csv", infer_schema_length=None)
    records = []
    with log:
        for row in summary.filter(pl.col("Pair").is_in(args.pairs)).iter_rows(named=True):
            BacktestingAPI._PRELOAD_CACHE_.clear()
            BacktestingAPI._TAPE_CACHE_.clear()
            weights = root() / row["Pair"] / f"Arm {row['Arm']}" / row["Job"] / "Output" / "Weights" / f"Seed {row['Seed']}" / "Fold 7"
            data = DDPGStrategyAPI.defaults("Backtesting")
            data["SignalManagement"]["Weights"] = [str(weights)]
            for name, flags in _variants_():
                target = root() / "Robustness" / row["Pair"] / name
                if not (target / "Output" / "Export" / "prices.csv").is_file():
                    mkdir(target, safe=False)
                    write_yaml(target / "Weights.yml", data, safe=False)
                    start, stop = WINDOWS["Full"]
                    SystemCommandAPI().main(["Backtesting", "--strategy", "DDPG", "--ticker", row["Pair"], "--timeframe", "Hour", "--resolution", "H1", "--start", start, "--stop", stop, "--account-asset", "USD", "--account-leverage", "30",
                                             *flags, "--parameters", str(target / "Weights.yml"), "--export", "--console", "Error", "--file", "Warning", "--run", str(target)])
                frame = _frame_(target)
                records.append({"Pair": row["Pair"], "Variant": name, **_curve_(frame["Timestamp"].to_list(), frame["Equity"].to_list(), "")})
                log.info(lambda row=row, name=name: f"Robustness Campaign: Completed · {row['Pair']} · {name}")
    table = pl.DataFrame(records)
    existing = root() / "Robustness.csv"
    if existing.is_file(): table = pl.concat([pl.read_csv(existing).filter(~pl.col("Pair").is_in(args.pairs)), table], how="diagonal_relaxed")
    table.sort(["Pair", "Variant"]).write_csv(existing)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())