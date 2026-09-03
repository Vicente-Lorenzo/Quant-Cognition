import re
import sys
import json
import os
import subprocess
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Library.Logging import LoggingAPI
from Library.Utility.Path import traceback_root

_TIMEOUT_: int = 10
_SOLVE_: int = 600
_ASSETS_: dict = {
    "lightweight-charts": Path("Library/App/V2/Assets/lightweight.js"),
}

def find_pinned(path: Path) -> str:
    if not path.is_file(): return ""
    found = re.search(r"v(\d+\.\d+\.\d+)", path.read_text(encoding="utf-8", errors="replace")[:400])
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

def plan(root: Path = None, timeout: int = _SOLVE_) -> tuple:
    from Setup.Environment import find_managers, find_manifest, find_root
    root = root if root is not None else traceback_root()
    environment = {**os.environ, "MAMBA_ROOT_PREFIX": str(find_root())}
    for manager in find_managers():
        try:
            raw = subprocess.run([manager, "env", "update", "--name", "Quant", "--file", str(find_manifest()),
                                  "--prune", "--dry-run", "--json"],
                                 capture_output=True, text=True, timeout=timeout, env=environment,
                                 **({"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}))
        except FileNotFoundError:
            continue
        except subprocess.TimeoutExpired:
            return [], f"Solve exceeded {timeout}s"
        body = (raw.stdout or "").strip()
        if not body.startswith("{"): continue
        try: report = json.loads(body)
        except json.JSONDecodeError: continue
        actions = report.get("actions") or {}
        linked = {entry["name"]: entry.get("version", "") for entry in actions.get("LINK", []) if entry.get("name")}
        unlinked = {entry["name"]: entry.get("version", "") for entry in actions.get("UNLINK", []) if entry.get("name")}
        changes = []
        for name in sorted(set(linked) | set(unlinked)):
            before, after = unlinked.get(name), linked.get(name)
            if before == after: continue
            changes.append({"name": name, "before": before, "after": after})
        return changes, None
    return [], "No environment manager found"

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