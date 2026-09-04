import sys
import subprocess
from pathlib import Path

def main() -> int:
    config = Path.home() / ".cloudflared" / "config.yml"
    return subprocess.run(["cloudflared", "--config", str(config), "tunnel", "run", "Quant"], stdout=sys.stdout, stderr=sys.stderr, creationflags=subprocess.CREATE_NO_WINDOW).returncode

if __name__ == "__main__":
    raise SystemExit(main())