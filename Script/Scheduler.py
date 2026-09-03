import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

if sys.stdout is None or sys.stderr is None:
    from Library.Logging.File import FileAPI
    _sink_ = FileAPI.folder() / "Scheduler.log"
    _sink_.parent.mkdir(parents=True, exist_ok=True)
    _handle_ = _sink_.open("w", buffering=1, encoding="utf-8-sig")
    sys.stdout = _handle_
    sys.stderr = _handle_

def main():
    try:
        from Library.Scheduler.Tray import main as serve
    except ImportError:
        import os
        import subprocess
        if "--relaunched" in sys.argv: raise
        conda = os.environ.get("CONDA_EXE", "conda")
        return subprocess.run(
            [conda, "run", "-n", "Quant", "--no-capture-output", "python", str(Path(__file__).resolve()), "--relaunched"],
            cwd=str(ROOT),
            **{"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
        ).returncode
    return serve()

if __name__ == "__main__":
    raise SystemExit(main())