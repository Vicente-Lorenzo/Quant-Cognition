import sys
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from Library.Utility.Runtime import windowless

def main() -> int:
    config = Path.home() / ".cloudflared" / "config.yml"
    return subprocess.run(["cloudflared", "--config", str(config), "tunnel", "run", "Quant"], stdout=sys.stdout, stderr=sys.stderr, **windowless()).returncode

if __name__ == "__main__":
    raise SystemExit(main())