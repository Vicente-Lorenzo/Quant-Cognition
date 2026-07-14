import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FOLDERS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".ipynb_checkpoints"}

def main():
    directories = [path for path in ROOT.rglob("*") if path.is_dir() and path.name in FOLDERS]
    files = [path for pattern in ("*.pyc", "*.pyo") for path in ROOT.rglob(pattern)]
    for path in directories: shutil.rmtree(path, ignore_errors=True)
    for path in files: path.unlink(missing_ok=True)
    print(f"Cache Clean: Completed · {len(directories)} Folders · {len(files)} Files")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())