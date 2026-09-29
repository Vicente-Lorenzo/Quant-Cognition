import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from Library.Data.Universe import UniverseServiceAPI
from Library.Logging import LoggingAPI, VerboseLevel

def main(database="Quant") -> int:
    log = LoggingAPI()
    log.console.set_level(VerboseLevel.Info)
    log.file.set_level(VerboseLevel.Info)
    with log:
        return UniverseServiceAPI(database=database).serve()

if __name__ == "__main__":
    raise SystemExit(main())