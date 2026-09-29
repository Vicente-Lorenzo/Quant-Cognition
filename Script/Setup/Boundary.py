import sys
from pathlib import Path
from argparse import ArgumentParser
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from Library.Utility.Datetime import utc_now
from Library.Utility.Path import inspect_persistent
from Library.Utility.IO import read_json, write_json
from Library.Logging import LoggingAPI, VerboseLevel
from Library.Database import PostgresDatabaseAPI
from Library.Database.Query import QueryAPI
from Script.Data.Market import MarketWorkerAPI
from Script.Data.Universe import UniverseServiceAPI
from Library.Market.Download import DownloadAPI, DownloadStatus
from Library.Market.Tape import TapeAPI
from Library.Market.Tick import TickAPI
from Library.Universe.Security import SecurityAPI

MARKER = inspect_persistent("Migrations") / "tape-boundary.json"
MILLISECOND = timedelta(milliseconds=1)

def _symbols_(db) -> dict:
    return {row["UID"]: int(row["Symbol"]) for row in db.records(schema=SecurityAPI.Schema, table=SecurityAPI.Table, columns=["UID", "Symbol"], condition='"Tracked" = TRUE')}

def _days_(db, before: datetime) -> list[tuple[int, int, datetime]]:
    symbols = _symbols_(db)
    rows = db.records(schema=DownloadAPI.Schema, table=DownloadAPI.Table, columns=["Security", "Timestamp"], condition='"Status" = :complete: AND "Timestamp" < :before:', parameters={"complete": DownloadStatus.Complete.name, "before": before})
    return sorted((row["Security"], symbols[row["Security"]], row["Timestamp"]) for row in rows if row["Security"] in symbols)

def _disordered_(db, before: datetime) -> list[tuple[int, int, datetime]]:
    symbols = _symbols_(db)
    frame = db.executeone(QueryAPI('''SELECT "Security", "Timestamp" FROM (SELECT "Security", "Timestamp", "UpdatedAt", LAG("UpdatedAt") OVER (PARTITION BY "Security" ORDER BY "Timestamp") AS "Previous"
        FROM "Market"."Download" WHERE "Status" = :complete:) AS "Ordered" WHERE "Previous" > "UpdatedAt" AND "Timestamp" < :before:'''), complete=DownloadStatus.Complete.name, before=before).fetchall(legacy=False)
    return sorted((security, symbols[security], day) for security, day in frame.rows() if security in symbols) if frame.height else []

def _repair_(api, db, security: int, symbol: int, day: datetime, before: datetime) -> int:
    end = day + timedelta(days=1)
    if db.first(schema="Market", table="Tick", columns=["UID"], condition='"UID" = :uid:', parameters={"uid": TickAPI.encode(security, end - MILLISECOND)}) is not None: return 0
    start = end - timedelta(seconds=2)
    asks, bids = (api.market.ticks(symbol, start, end, quote=side, legacy=False) for side in ("Ask", "Bid"))
    if not asks.height and not bids.height: return 0
    restored = TapeAPI.extend(db, security, TapeAPI.merge(asks, bids, TapeAPI.previous(db, security, start)), end - MILLISECOND, "Market")
    following = DownloadAPI.successor(db, security, day, before) if restored else None
    if following is not None: MarketWorkerAPI.rewrite(api, db, security, symbol, following)
    return restored

def _share_(service, account: int, database: str, work, items: list, log) -> int:
    done = 0
    with service.client(account) as api, PostgresDatabaseAPI(database=database) as db:
        for index, item in enumerate(items):
            done += work(api, db, *item)
            if index and index % 2000 == 0: log.info(lambda index=index, item=item: f"Tape Boundary: Progress · {index:,}/{len(items):,} · {item[-1]:%Y-%m-%d}")
    return done

def _spread_(service, account: int, database: str, connections: int, work, items: list, log) -> int:
    with ThreadPoolExecutor(max_workers=connections) as pool:
        return sum(pool.map(lambda share: _share_(service, account, database, work, share, log), [items[index::connections] for index in range(connections)]))

def main(database: str = "Quant", apply: bool = False, connections: int = 4, vault: str = "Quant") -> int:
    log = LoggingAPI()
    log.console.set_level(VerboseLevel.Info)
    with log:
        applied = read_json(MARKER).get("Applied") if database == "Quant" else None
        if apply and applied:
            log.error(lambda: f"Tape Boundary: Refused · Already Applied {applied}")
            return 1
        before = utc_now().replace(hour=0, minute=0, second=0, microsecond=0)
        with PostgresDatabaseAPI(database=database) as db: days, disordered = _days_(db, before), _disordered_(db, before)
        log.info(lambda: f"Tape Boundary: Plan · {len(disordered):,} Days Written Before Their Predecessor · {len(days):,} Complete Days · {10 * len(disordered) + 2 * len(days):,} Requests · {(10 * len(disordered) + 2 * len(days)) / (4.0 * connections) / 3600:.1f}h On {connections} Connections")
        if not apply:
            log.info(lambda: "Tape Boundary: Dry Run · Nothing Changed · Pass --apply")
            return 0
        service = UniverseServiceAPI(database=database, vault=vault)
        account = int([account for account in service.accounts() if account.get("Broker")][-1]["AccountId"])
        rewritten = _spread_(service, account, database, connections, lambda api, db, security, symbol, day: int(MarketWorkerAPI.rewrite(api, db, security, symbol, day) is DownloadStatus.Complete), disordered, log)
        log.info(lambda: f"Tape Boundary: Carried · {rewritten} Days Rewritten After Their Predecessor")
        restored = _spread_(service, account, database, connections, lambda api, db, security, symbol, day: _repair_(api, db, security, symbol, day, before), days, log)
        log.info(lambda: f"Tape Boundary: Completed · {restored} Ticks Restored · {len(days):,} Days Checked · {rewritten} Days Rewritten")
        if database == "Quant": write_json(MARKER, {"Applied": utc_now().isoformat(sep=" ", timespec="seconds"), "Days": len(days), "Restored": restored, "Rewritten": rewritten})
        return 0

if __name__ == "__main__":
    parser = ArgumentParser(prog="Boundary")
    parser.add_argument("--database", default="Quant")
    parser.add_argument("--vault", default="Quant")
    parser.add_argument("--connections", type=int, default=4)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    raise SystemExit(main(args.database, args.apply, args.connections, args.vault))