import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

def main():
    try:
        from Library.Web.Serve import main as serve
    except ImportError:
        import os
        import subprocess
        if "--relaunched" in sys.argv: raise
        conda = os.environ.get("CONDA_EXE", "conda")
        return subprocess.run([conda, "run", "-n", "Quant", "--no-capture-output", "python", str(Path(__file__).resolve()), "--relaunched"], cwd=str(ROOT)).returncode
    return serve()

if __name__ == "__main__":
    raise SystemExit(main())