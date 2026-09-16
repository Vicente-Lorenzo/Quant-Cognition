import sys
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from Script.Environment.Cache import ROOT, clean
from Library.Utility.Runtime import windowless

REQUIREMENTS = ROOT / "Requirements.txt"

def main():
    clean()
    if not REQUIREMENTS.is_file():
        print(f"UV Update: Skipped · {REQUIREMENTS.name} Absent · Use Conda.py for the Quant environment")
        return 0
    subprocess.run(["uv", "pip", "install", "--system", "--upgrade", "-r", str(REQUIREMENTS)], check=True, **windowless())
    print(f"UV Update: Completed · {REQUIREMENTS.name}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())