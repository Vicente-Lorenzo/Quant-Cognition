import sys
from pathlib import Path
from argparse import ArgumentParser

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from Library.Utility.Datetime import utc_now
from Library.Utility.Path import inspect_persistent
from Library.Utility.IO import read_json, write_json
from Library.Logging import LoggingAPI, VerboseLevel
from Library.Database import PostgresDatabaseAPI, QueryAPI

ZONE = "Europe/London"
MARKER = inspect_persistent("Migrations") / "timezone-utc.json"

COLUMNS = {
    ("Auth", "Office"): ("UpdatedAt",),
    ("Auth", "Team"): ("UpdatedAt",),
    ("Auth", "User"): ("LastLogin", "UpdatedAt"),
    ("Indicator", "Calendar"): ("UpdatedAt",),
    ("Logging", "Log"): ("StartedAt", "StoppedAt", "UpdatedAt"),
    ("Portfolio", "Account"): ("Timestamp", "UpdatedAt"),
    ("Portfolio", "Order"): ("UpdatedAt",),
    ("Portfolio", "Position"): ("UpdatedAt",),
    ("Portfolio", "Session"): ("StartTimestamp", "StopTimestamp", "UpdatedAt"),
    ("Portfolio", "Trade"): ("UpdatedAt",),
    ("Scheduler", "Cycle"): ("StartedAt", "StoppedAt", "UpdatedAt"),
    ("Scheduler", "Dependency"): ("UpdatedAt",),
    ("Scheduler", "Run"): ("Heartbeat", "StartedAt", "StoppedAt", "UpdatedAt"),
    ("Scheduler", "Task"): ("UpdatedAt",),
    ("Scheduler", "Workflow"): ("UpdatedAt",),
    ("Universe", "Category"): ("UpdatedAt",),
    ("Universe", "Contract"): ("UpdatedAt",),
    ("Universe", "Provider"): ("UpdatedAt",),
    ("Universe", "Security"): ("UpdatedAt",),
    ("Universe", "Ticker"): ("UpdatedAt",),
    ("Universe", "Timeframe"): ("UpdatedAt",)
}

def _shifted_(db, schema: str, table: str, column: str, zone: str) -> dict:
    quoted = db._quoted_(column)
    sql = f'SELECT COUNT({quoted}) AS "Rows", MIN({quoted}) AS "Oldest", MAX({quoted}) AS "Newest", MIN(({quoted} AT TIME ZONE :zone:) AT TIME ZONE \'UTC\') AS "Shifted" FROM {db._target_(schema, table)}'
    return db.executeone(QueryAPI(sql), zone=zone).fetchall(legacy=False).row(0, named=True)

def _convert_(db, schema: str, table: str, column: str, zone: str) -> None:
    quoted = db._quoted_(column)
    sql = f'UPDATE {db._target_(schema, table)} SET {quoted} = ({quoted} AT TIME ZONE :zone:) AT TIME ZONE \'UTC\' WHERE {quoted} IS NOT NULL'
    db.executeone(QueryAPI(sql), zone=zone)

def _apply_(database: str, zone: str, plan: list) -> None:
    with PostgresDatabaseAPI(database=database, autocommit=False) as db:
        for schema, table, column, _ in plan: _convert_(db, schema, table, column, zone)
        db.commit()

def _plan_(log, database: str, zone: str) -> list:
    plan = []
    with PostgresDatabaseAPI(database=database) as db:
        for (schema, table), columns in COLUMNS.items():
            for column in columns:
                try: summary = _shifted_(db, schema, table, column, zone)
                except Exception as error:
                    log.warning(lambda schema=schema, table=table, column=column, error=error: f"Timezone Inspect: Skipped ({schema}.{table}.{column}) · Due to {error}")
                    continue
                if summary["Rows"]: plan.append((schema, table, column, summary))
    return plan

def main(database: str = "Quant", zone: str = ZONE, apply: bool = False, force: bool = False) -> int:
    with LoggingAPI() as log:
        applied = read_json(MARKER).get("Applied")
        if apply and not force and applied:
            log.error(lambda: f"Timezone Migration: Refused · Already Applied {applied}")
            return 1
        plan = _plan_(log, database, zone)
        rows = sum(summary["Rows"] for _, _, _, summary in plan)
        for schema, table, column, summary in plan:
            log.info(lambda schema=schema, table=table, column=column, summary=summary: f"Timezone Column: {'Converting' if apply else 'Planned'} ({schema}.{table}.{column}) · {summary['Rows']} Rows · {summary['Oldest']} to {summary['Shifted']}")
        if not apply:
            log.info(lambda: f"Timezone Migration: Planned · {rows} Rows · {len(plan)} Columns · {zone} to UTC · Pass --apply to Write")
            return 0
        try: _apply_(database, zone, plan)
        except Exception as error:
            log.failure(lambda error=error: f"Timezone Migration: Failed · Due to {error} · Rolled Back")
            return 1
        write_json(MARKER, {"Applied": str(utc_now()), "Zone": zone, "Database": database, "Columns": len(plan), "Rows": rows})
        log.info(lambda: f"Timezone Migration: Completed · {rows} Rows · {len(plan)} Columns · {zone} to UTC")
        return 0

if __name__ == "__main__":
    parser = ArgumentParser(prog="Timezone", description="Converts locally stamped timestamp columns to naive UTC")
    parser.add_argument("--database", default="Quant")
    parser.add_argument("--zone", default=ZONE)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--force", action="store_true")
    arguments = parser.parse_args()
    log = LoggingAPI()
    log.console.set_level(VerboseLevel.Info)
    log.file.set_level(VerboseLevel.Debug)
    raise SystemExit(main(database=arguments.database, zone=arguments.zone, apply=arguments.apply, force=arguments.force))