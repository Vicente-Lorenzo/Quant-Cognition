import os
import subprocess
from pathlib import Path

from Cache import clean

ROOT = Path(__file__).resolve().parent.parent
MAMBA = os.environ.get("MAMBA_EXE") or "mamba"
ENVIRONMENTS = {"Quant": ROOT / "Quant.yml", "Future": ROOT / "Future.yml", "Exotics": ROOT / "Exotics.yml"}

def _base_():
    conda = os.environ.get("CONDA_EXE", "conda")
    try: result = subprocess.run([conda, "info", "--base"], capture_output=True, text=True)
    except FileNotFoundError: return None
    return Path(result.stdout.strip()) if result.returncode == 0 and result.stdout.strip() else None

def _exists_(base, name):
    if base is None: return True
    return (base / "envs" / name / "conda-meta" / "history").is_file()

def ensure_environment(base, name, manifest):
    if not manifest.is_file():
        print(f"Conda Update: Skipped · {manifest.name} Absent")
        return
    verb = "update" if _exists_(base, name) else "create"
    command = [MAMBA, "env", verb, "--name", name, "--file", str(manifest)]
    if verb == "update": command.append("--prune")
    subprocess.run(command, check=True)

def main():
    clean()
    os.environ["CONDA_ALWAYS_YES"] = "true"
    base = _base_()
    for name, manifest in ENVIRONMENTS.items(): ensure_environment(base, name, manifest)
    print(f"Conda Update: Completed · {len(ENVIRONMENTS)} Environments")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())