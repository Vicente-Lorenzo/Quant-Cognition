import re
import sys
import json
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from Library.Logging import LoggingAPI
from Library.Utility.IO import read_text
from Library.Utility.Path import traceback_root
from Script.Task import attempt

_TIMEOUT_: int = 10
_ASSETS_: dict = {
    "lightweight-charts": Path("Library/App/V2/Assets/lightweight.js"),
}

def find_pinned(path: Path) -> str:
    found = re.search(r"v(\d+\.\d+\.\d+)", read_text(path, errors="replace")[:400])
    return found.group(1) if found else ""

def find_latest(package: str, timeout: int = _TIMEOUT_) -> str:
    with urllib.request.urlopen(f"https://registry.npmjs.org/{package}/latest", timeout=timeout) as response:
        return json.loads(response.read()).get("version", "")

def find_assets(root: Path = None, assets: dict = None) -> list:
    root = root if root is not None else traceback_root()
    findings = []
    for package, relative in (assets if assets is not None else _ASSETS_).items():
        pinned = find_pinned(root / relative)
        try: latest, reason = find_latest(package), None
        except Exception as error: latest, reason = "", error
        findings.append({"name": package, "pinned": pinned, "latest": latest, "reason": reason})
    return findings

def main() -> int:
    with LoggingAPI() as log:
        def work():
            outdated = 0
            for finding in find_assets():
                name, pinned, latest, reason = finding["name"], finding["pinned"], finding["latest"], finding["reason"]
                if reason is not None: log.warning(lambda n=name, r=reason: f"Version Asset: Skipped ({n}) · Due to {r}")
                elif not pinned: log.warning(lambda n=name: f"Version Asset: Unknown ({n}) · Pinned version not found in the vendored header")
                elif pinned == latest: log.info(lambda n=name, v=pinned: f"Version Asset: Current ({n}) · {v}")
                else:
                    outdated += 1
                    log.alert(lambda n=name, a=pinned, b=latest: f"Version Asset: Outdated ({n}) · {a} → {b} · Upgrade deliberately and verify a rendered plot")
            return f"{outdated} Outdated Assets"
        return attempt(log, "Version", work, operation="Check")

if __name__ == "__main__":
    raise SystemExit(main())