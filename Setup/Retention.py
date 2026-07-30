import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Library.Logging import LoggingAPI
from Library.Logging.File import FileAPI
from Library.Logging.Log import LogAPI
from Library.Database import PostgresDatabaseAPI
from Library.Scheduler.Executor import ExecutorAPI

_FOLDERS_: tuple = (FileAPI.folder(), Path(ExecutorAPI.RUNS))
_PATTERNS_: tuple = ("*.log", "*.log.*")
_DAYS_: int = 30

def prune_files(folders=_FOLDERS_, days: int = _DAYS_) -> tuple[int, int]:
    horizon, removed, reclaimed = time.time() - days * 86400, 0, 0
    for folder in folders:
        if not folder.is_dir(): continue
        for pattern in _PATTERNS_:
            for candidate in folder.glob(pattern):
                try:
                    if not candidate.is_file() or candidate.stat().st_mtime >= horizon: continue
                    reclaimed += candidate.stat().st_size
                    candidate.unlink()
                    removed += 1
                except OSError:
                    continue
    return removed, reclaimed

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