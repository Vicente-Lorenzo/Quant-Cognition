import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Library.Utility.File import PruneAPI
from Library.Utility.Path import traceback_root

ROOT = traceback_root()
FOLDERS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".ipynb_checkpoints", ".hypothesis", ".tox", ".nox", "htmlcov"}
BUILDS = {"bin", "obj"}
PATTERNS = ("*.pyc", "*.pyo", "*.pstat")
DAYS = 30

def collect(root=ROOT):
    folders = [path for path in root.rglob("*") if path.is_dir() and path.name in FOLDERS]
    folders += [path for path in (root / "Sources").rglob("*") if path.is_dir() and path.name in BUILDS]
    files = [path for pattern in PATTERNS for path in root.rglob(pattern)]
    return folders, files

def clean(root=ROOT, days=DAYS):
    folders, files = collect(root)
    cleaned, reclaimed = 0, 0
    horizon = time.time() - days * 86400
    for candidate in folders + files:
        if not candidate.exists() or not PruneAPI.stale(candidate, horizon): continue
        size = PruneAPI.discard(candidate)
        if not size and candidate.exists(): continue
        cleaned += 1
        reclaimed += size
    return cleaned, reclaimed

def main(days=DAYS):
    cleaned, reclaimed = clean(days=days)
    print(f"Cache Clean: Completed · {cleaned} Entries · {reclaimed / 1048576:.1f} MB · {days} Days")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())