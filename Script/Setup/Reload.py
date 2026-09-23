import sys
from pathlib import Path
from argparse import ArgumentParser

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from Library.Database import PostgresDatabaseAPI, QueryAPI
from Library.Logging import LoggingAPI, VerboseLevel
from Library.Market.Tick import TickAPI
from Library.Utility.Datetime import utc_now
from Library.Utility.IO import read_json, write_json
from Library.Utility.Path import inspect_persistent
from Library.Utility.Profiler import Timer

SOURCE = "Tick"
TARGET = "TickReload"
MARKER = inspect_persistent("Migrations") / "tick-reload.json"
INTERVAL = 31 * 86400 * 1000
COLUMNS = ("UID", "Security", "Timestamp", "Ask", "Mid", "Bid", "Volume", "AskBaseConversion", "BidBaseConversion", "AskQuoteConversion", "BidQuoteConversion", "UpdatedAt", "UpdatedBy")

def _create_(db, schema: str) -> None:
    target = db._target_(schema, TARGET)
    db.executeone(QueryAPI(f'''CREATE TABLE IF NOT EXISTS {target} ("UID" BIGINT NOT NULL, "Security" BIGINT NOT NULL, "Timestamp" TIMESTAMPTZ NOT NULL,
        "Ask" DOUBLE PRECISION, "Mid" DOUBLE PRECISION, "Bid" DOUBLE PRECISION, "Volume" DOUBLE PRECISION,
        "AskBaseConversion" DOUBLE PRECISION, "BidBaseConversion" DOUBLE PRECISION, "AskQuoteConversion" DOUBLE PRECISION, "BidQuoteConversion" DOUBLE PRECISION,
        "UpdatedAt" TIMESTAMPTZ, "UpdatedBy" VARCHAR, PRIMARY KEY ("UID"))'''))
    db.executeone(QueryAPI(f"SELECT create_hypertable('{target}', by_range('UID', {INTERVAL}), if_not_exists => TRUE)"))
    db.executeone(QueryAPI(f'''ALTER TABLE {target} SET (timescaledb.compress, timescaledb.compress_segmentby = '"Security"', timescaledb.compress_orderby = '"UID"')'''))

def _units_(db, schema: str) -> list:
    source, units, low = db._target_(schema, SOURCE), [], 0
    while True:
        first = db.executeone(QueryAPI(f'SELECT MIN("UID") AS "UID" FROM {source} WHERE "UID" >= :low:'), low=low).fetchall(legacy=False).item()
        if first is None: return units
        security = first >> TickAPI._MS_BITS_
        low = (security + 1) << TickAPI._MS_BITS_
        last = db.executeone(QueryAPI(f'SELECT MAX("UID") AS "UID" FROM {source} WHERE "UID" < :low:'), low=low).fetchall(legacy=False).item()
        units.extend((security, index * INTERVAL, (index + 1) * INTERVAL - 1) for index in range(first // INTERVAL, last // INTERVAL + 1))

def _hash_(db, schema: str, table: str, low: int, high: int) -> tuple:
    sql = f'''SELECT COUNT(*) AS "Rows", COALESCE(BIT_XOR(HASHTEXTEXTENDED(CONCAT_WS('|', "UID", "Security", CAST("Timestamp" AS TIMESTAMP), "Ask", "Mid", "Bid", "Volume",
        "AskBaseConversion", "BidBaseConversion", "AskQuoteConversion", "BidQuoteConversion", CAST("UpdatedAt" AS TIMESTAMP), "UpdatedBy"), 0)), 0) AS "Hash"
        FROM {db._target_(schema, table)} WHERE "UID" BETWEEN :low: AND :high:'''
    row = db.executeone(QueryAPI(sql), low=low, high=high).fetchall(legacy=False).row(0, named=True)
    return int(row["Rows"]), int(row["Hash"])

def _reload_(db, schema: str, low: int, high: int) -> tuple:
    source, target = db._target_(schema, SOURCE), db._target_(schema, TARGET)
    columns = db._quoted_(*COLUMNS)
    db.executeone(QueryAPI(f'DELETE FROM {target} WHERE "UID" BETWEEN :low: AND :high:'), low=low, high=high)
    db.executeone(QueryAPI(f'INSERT INTO {target} ({columns}) SELECT {columns} FROM {source} WHERE "UID" BETWEEN :low: AND :high:'), low=low, high=high)
    expected, produced = _hash_(db, schema, SOURCE, low, high), _hash_(db, schema, TARGET, low, high)
    if expected != produced: raise ValueError(f"Rows {produced[0]} Against {expected[0]} · Hash {produced[1]} Against {expected[1]}")
    if expected[0]: db.executeone(QueryAPI("SELECT compress_chunk((QUOTE_IDENT(chunk_schema) || '.' || QUOTE_IDENT(chunk_name))::REGCLASS, TRUE) FROM timescaledb_information.chunks WHERE hypertable_schema = :schema: AND hypertable_name = :table: AND NOT is_compressed AND range_start_integer = :low:"), schema=schema, table=TARGET, low=low)
    return expected

def main(database: str = "Quant", schema: str = "Market", apply: bool = False, limit: int = 0) -> int:
    with LoggingAPI() as log:
        marker = MARKER.with_name(f"{MARKER.stem}-{database}-{schema}{MARKER.suffix}")
        progress = read_json(marker)
        done = progress.setdefault("Units", {})
        with PostgresDatabaseAPI(database=database) as db:
            units = _units_(db, schema)
            pending = [unit for unit in units if f"{unit[0]}:{unit[1]}" not in done]
            log.info(lambda: f"Reload Plan: {'Building' if apply else 'Planned'} · {len(units)} Units · {len(units) - len(pending)} Done · {len(pending)} Pending · {schema}.{SOURCE} to {schema}.{TARGET}")
            if not apply:
                log.info(lambda: "Reload Plan: Dry Run · Pass --apply to Build")
                return 0
            db.executeone(QueryAPI("SET synchronous_commit = off"))
            _create_(db, schema)
            for security, low, high in pending[:limit] if limit else pending:
                watch = Timer().start()
                try: rows, digest = _reload_(db, schema, low, high)
                except Exception as error:
                    log.failure(lambda error=error, security=security, low=low: f"Reload Unit: Failed ({security}:{low}) · Due to {error}")
                    return 1
                watch.stop()
                done[f"{security}:{low}"] = {"Rows": rows, "Hash": digest, "Seconds": round(watch.delta(), 3)}
                progress["UpdatedAt"] = str(utc_now())
                write_json(marker, progress)
                log.info(lambda security=security, low=low, rows=rows, watch=watch: f"Reload Unit: Completed ({security}:{low}) · {rows} Rows · {watch.result()} · {len(done)}/{len(units)}")
        log.info(lambda: f"Reload Build: {'Completed' if len(done) == len(units) else 'Paused'} · {len(done)}/{len(units)} Units · {sum(entry['Rows'] for entry in done.values())} Rows")
        return 0

if __name__ == "__main__":
    parser = ArgumentParser(prog="Reload", description="Rebuilds Market.Tick as a compressed timestamptz hypertable beside the original, one verified chunk at a time")
    parser.add_argument("--database", default="Quant")
    parser.add_argument("--schema", default="Market")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    arguments = parser.parse_args()
    log = LoggingAPI()
    log.console.set_level(VerboseLevel.Info)
    log.file.set_level(VerboseLevel.Debug)
    raise SystemExit(main(database=arguments.database, schema=arguments.schema, apply=arguments.apply, limit=arguments.limit))