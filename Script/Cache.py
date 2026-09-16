import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Library.Utility.File import PruneAPI
from Library.Utility.Memory import memory_to_string
from Library.Utility.Path import traceback_root

ROOT = traceback_root()
FOLDERS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".ipynb_checkpoints", ".hypothesis", ".tox", ".nox", "htmlcov"}
BUILDS = {"bin", "obj"}
PATTERNS = ("*.pyc", "*.pyo", "*.pstat")
DAYS = PruneAPI.DAYS

def collect(root=ROOT):
    folders = [path for path in root.rglob("*") if path.is_dir() and path.name in FOLDERS]
    folders += [path for path in (root / "Sources").rglob("*") if path.is_dir() and path.name in BUILDS]
    files = [path for pattern in PATTERNS for path in root.rglob(pattern)]
    return folders, files

def clean(root=ROOT, days=DAYS):
    folders, files = collect(root)
    return PruneAPI.sweep(folders + files, PruneAPI.horizon(days))

def main(days=DAYS):
    cleaned, reclaimed = clean(days=days)
    print(f"Cache Clean: Completed · {cleaned} Entries · {memory_to_string(reclaimed)} · {days} Days")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())