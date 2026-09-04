import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Library.Logging import LoggingAPI
from Library.Logging.Log import LogAPI
from Library.Database import PostgresDatabaseAPI
from Library.Logging.File import FileAPI
from Library.Scheduler.Executor import ExecutorAPI
from Library.System.System import SystemAPI
from Library.Utility.File import PruneAPI
from Library.Utility.Path import inspect_cached, inspect_temporary
from Library.Utility.Profiler import PROFILES

_DAYS_: int = 30

def temporaries() -> tuple:
    root = inspect_temporary()
    declared = tuple(inspect_temporary(name) for name in (FileAPI.Folder, ExecutorAPI.Folder, SystemAPI.Exports, SystemAPI.Plots, PROFILES))
    if not root.is_dir(): return declared
    return tuple(dict.fromkeys((*declared, *(entry for entry in root.iterdir() if entry.is_dir()))))

def caches() -> tuple:
    root = inspect_cached()
    return tuple(entry for entry in root.iterdir() if entry.is_dir()) if root.is_dir() else ()

def prune_files(folders=None, days: int = _DAYS_) -> tuple[int, int]:
    return PruneAPI.prune(folders if folders is not None else (*temporaries(), *caches()), days=days)

def prune_records(database: str = "Quant", days: int = _DAYS_) -> int:
    with PostgresDatabaseAPI(database=database) as db:
        return LogAPI.prune(db=db, days=days)

def main(database: str = "Quant", days: int = _DAYS_) -> int:
    with LoggingAPI() as log:
        try:
            removed, reclaimed = prune_files(days=days)
            log.info(lambda: f"Retention Files: Completed · {removed} Files · {reclaimed / 1048576:.1f} MB · {days} Days")
        except Exception as error:
            log.exception(lambda: f"Retention Files: Failed · Due to {error}")
            return 1
        try:
            records = prune_records(database=database, days=days)
            log.info(lambda: f"Retention Records: Completed · {records} Rows · {days} Days")
        except Exception as error:
            log.warning(lambda: f"Retention Records: Skipped · Due to {error}")
        return 0

if __name__ == "__main__":
    raise SystemExit(main())