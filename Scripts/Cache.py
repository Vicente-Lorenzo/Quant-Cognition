import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FOLDERS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".ipynb_checkpoints"}
BUILDS = {"bin", "obj"}

def clean(root=ROOT):
    directories = [path for path in root.rglob("*") if path.is_dir() and path.name in FOLDERS]
    directories += [path for path in (root / "Sources").rglob("*") if path.is_dir() and path.name in BUILDS]
    files = [path for pattern in ("*.pyc", "*.pyo") for path in root.rglob(pattern)]
    for path in directories: shutil.rmtree(path, ignore_errors=True)
    for path in files: path.unlink(missing_ok=True)
    return len(directories), len(files)

def main():
    directories, files = clean()
    print(f"Cache Clean: Completed · {directories} Folders · {files} Files")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
