import re
import sys
import json
import subprocess
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Library.Logging import LoggingAPI
from Library.Utility.IO import read_text
from Library.Utility.Path import traceback_root

_TIMEOUT_: int = 10
_SOLVE_: int = 600
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

def _report_(raw: subprocess.CompletedProcess) -> dict | None:
    body = (raw.stdout or "").strip()
    if not body.startswith("{"): return None
    try: return json.loads(body)
    except json.JSONDecodeError: return None

def plan(root: Path = None, timeout: int = _SOLVE_) -> tuple:
    from Setup.Environment import find_manifest, run_manager
    root = root if root is not None else traceback_root()
    try: raw = run_manager(["env", "update", "--name", "Quant", "--file", str(find_manifest()), "--prune", "--dry-run", "--json"], accept=_report_, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError: return [], "No environment manager found"
    except subprocess.TimeoutExpired: return [], f"Solve exceeded {timeout}s"
    actions = _report_(raw).get("actions") or {}
    linked = {entry["name"]: entry.get("version", "") for entry in actions.get("LINK", []) if entry.get("name")}
    unlinked = {entry["name"]: entry.get("version", "") for entry in actions.get("UNLINK", []) if entry.get("name")}
    changes = []
    for name in sorted(set(linked) | set(unlinked)):
        before, after = unlinked.get(name), linked.get(name)
        if before == after: continue
        changes.append({"name": name, "before": before, "after": after})
    return changes, None

def main() -> int:
    with LoggingAPI() as log:
        outdated = 0
        for finding in find_assets():
            name, pinned, latest, reason = finding["name"], finding["pinned"], finding["latest"], finding["reason"]
            if reason is not None: log.warning(lambda n=name, r=reason: f"Version Asset: Skipped ({n}) · Due to {r}")
            elif not pinned: log.warning(lambda n=name: f"Version Asset: Unknown ({n}) · Pinned version not found in the vendored header")
            elif pinned == latest: log.info(lambda n=name, v=pinned: f"Version Asset: Current ({n}) · {v}")
            else:
                outdated += 1
                log.alert(lambda n=name, a=pinned, b=latest: f"Version Asset: Outdated ({n}) · {a} → {b} · Upgrade deliberately and verify a rendered plot")
        changes, reason = plan()
        if reason is not None: log.warning(lambda r=reason: f"Version Environment: Skipped · Due to {r}")
        elif not changes: log.info(lambda: "Version Environment: Current · Update would change nothing")
        else:
            for change in changes:
                kind = "Upgrade" if change["before"] and change["after"] else ("Install" if change["after"] else "Remove")
                log.alert(lambda c=change, k=kind: f"Version Environment: {k} ({c['name']}) · {c['before'] or '-'} → {c['after'] or '-'}")
        log.info(lambda: f"Version Check: Completed · {outdated} Outdated Assets · {len(changes)} Pending Environment Changes")
        return 0

if __name__ == "__main__":
    raise SystemExit(main())