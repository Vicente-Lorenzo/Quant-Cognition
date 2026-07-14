import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def main():
    executable = shutil.which("claude") or "claude"
    return subprocess.run([executable, "--dangerously-skip-permissions"], cwd=str(ROOT)).returncode

if __name__ == "__main__":
    raise SystemExit(main())