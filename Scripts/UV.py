import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REQUIREMENTS = ROOT / "Requirements.txt"

def main():
    if not REQUIREMENTS.is_file():
        print(f"UV Update: Skipped · {REQUIREMENTS.name} Absent · Use Conda.py for the Quant environment")
        return 0
    subprocess.run(["uv", "pip", "install", "--system", "--upgrade", "-r", str(REQUIREMENTS)], check=True)
    print(f"UV Update: Completed · {REQUIREMENTS.name}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
