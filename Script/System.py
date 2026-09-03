import sys
import subprocess

from Cache import ROOT, clean, windowless

REQUIREMENTS = ROOT / "Requirements.txt"

def main():
    clean()
    subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], check=True, **windowless())
    if not REQUIREMENTS.is_file():
        print(f"System Update: Skipped · {REQUIREMENTS.name} Absent · Use Conda.py for the Quant environment")
        return 0
    subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "-r", str(REQUIREMENTS)], check=True, **windowless())
    print(f"System Update: Completed · {REQUIREMENTS.name}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())