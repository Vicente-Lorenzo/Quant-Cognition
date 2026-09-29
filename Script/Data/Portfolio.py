import sys
from pathlib import Path
from argparse import ArgumentParser

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from Library.Data.Portfolio import PortfolioServiceAPI, PortfolioWorkerAPI
from Library.Logging import LoggingAPI, VerboseLevel
from Script.Data.Horizon import HORIZON

def main() -> int:
    parser = ArgumentParser(prog="Portfolio")
    parser.add_argument("--account", type=int, default=None)
    parser.add_argument("--database", default="Quant")
    args = parser.parse_args()
    worker, log = args.account is not None, LoggingAPI()
    log.console.set_level(VerboseLevel.Warning if worker else VerboseLevel.Info)
    log.file.set_level(VerboseLevel.Warning if worker else VerboseLevel.Info)
    with log:
        if worker: return PortfolioWorkerAPI(account=args.account, horizon=HORIZON, database=args.database).serve()
        return PortfolioServiceAPI(script=Path(__file__).resolve(), database=args.database).serve()

if __name__ == "__main__":
    raise SystemExit(main())