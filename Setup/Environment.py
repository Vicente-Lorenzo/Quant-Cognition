import os
import sys
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Library.Logging import HandlerLoggingAPI

MANIFEST = Path(__file__).resolve().parent.parent / "Quant.yml"

def update_environment():
    candidates = [os.environ.get("MAMBA_EXE"), "mamba", os.environ.get("CONDA_EXE"), "conda"]
    for manager in [name for name in candidates if name]:
        try: return subprocess.run([manager, "env", "update", "--name", "Quant", "--file", str(MANIFEST), "--prune"], check=True, stdout=sys.stdout, stderr=sys.stderr, creationflags=subprocess.CREATE_NO_WINDOW)
        except FileNotFoundError: continue
    raise FileNotFoundError("Conda or Mamba executable not found")

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