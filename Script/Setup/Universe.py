import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from Library.Utility.Datetime import utc_now
from Library.Database.Dataframe import pl
from Library.Logging import LoggingAPI
from Script.Task import migrate, provision
from Library.Universe.Universe import UniverseAPI
from Library.Universe.Ticker import TickerAPI
from Library.Universe.Contract import ContractAPI
from Library.Universe.Security import SecurityAPI
from Library.Universe.Category import CategoryAPI
from Library.Universe.Timeframe import TimeframeAPI
from Library.Universe.Provider import ProviderAPI

TIMEFRAMES = ["M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9", "M10", "M15", "M20", "M30", "M45", "H1", "H2", "H3", "H4", "H6", "H8", "H12", "D1", "D2", "D3", "W1", "MN1"]

def populate_universe(db):
    migrate(db, CategoryAPI, ProviderAPI, TickerAPI, SecurityAPI, ContractAPI, TimeframeAPI)
    UniverseAPI.push_timeframes(db, pl.DataFrame([{str(TimeframeAPI.ID.UID): timeframe} for timeframe in TIMEFRAMES]).with_columns(pl.lit(utc_now()).alias("UpdatedAt"), pl.lit("Population").alias("UpdatedBy")))
    return f"Schema + 6 Tables · {len(TIMEFRAMES)} Timeframes · Catalog From The Universe Service"

def main(database="Quant"):
    with LoggingAPI() as log:
        return provision(log, "Universe", populate_universe, database=database)

if __name__ == "__main__":
    raise SystemExit(main())