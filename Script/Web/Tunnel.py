import sys
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from Library.Utility.Progress import Phase, ProgressAPI
from Library.Utility.Runtime import windowless

def main() -> int:
    config = Path.home() / ".cloudflared" / "config.yml"
    process = subprocess.Popen(["cloudflared", "--config", str(config), "tunnel", "run", "Quant"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", **windowless())
    ready = False
    for line in process.stdout:
        sys.stdout.write(line)
        sys.stdout.flush()
        if not ready and "Registered tunnel connection" in line:
            ready = True
            ProgressAPI.phase(Phase.Running)
    ProgressAPI.phase(Phase.Terminating)
    return process.wait()

if __name__ == "__main__":
    raise SystemExit(main())