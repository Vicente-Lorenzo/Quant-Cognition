import os
import sys
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Library.Logging import HandlerLoggingAPI

MANIFEST = Path(__file__).resolve().parent.parent / "Quant.yml"

def find_root() -> Path:
    interpreter = Path(sys.executable).resolve()
    return interpreter.parents[2] if (interpreter.parents[2] / "condabin").is_dir() else interpreter.parent

def find_managers() -> list:
    root = find_root()
    folders = (root / "Scripts", root / "Library" / "bin")
    found = [os.environ.get("MAMBA_EXE")] + [str(path) for folder in folders if (path := folder / "mamba.exe").is_file()]
    found += [os.environ.get("CONDA_EXE")] + [str(path) for folder in folders if (path := folder / "conda.exe").is_file()]
    found += ["mamba", "conda"]
    return list(dict.fromkeys(name for name in found if name))

def update_environment():
    environment = {**os.environ, "MAMBA_ROOT_PREFIX": str(find_root())}
    for manager in find_managers():
        try: return subprocess.run([manager, "env", "update", "--name", "Quant", "--file", str(MANIFEST), "--prune"], check=True, env=environment, stdout=sys.stdout, stderr=sys.stderr, creationflags=subprocess.CREATE_NO_WINDOW)
        except FileNotFoundError: continue
    raise FileNotFoundError("Mamba or Conda executable not found")

def main():
    with HandlerLoggingAPI(Class="Setup", Subclass="Environment") as log:
        try:
            update_environment()
            log.info(lambda: f"Environment Setup: Completed · {MANIFEST.name}")
            return 0
        except Exception as error:
            log.exception(lambda: f"Environment Setup: Failed · Due to {error}")
            return 1

if __name__ == "__main__":
    raise SystemExit(main())