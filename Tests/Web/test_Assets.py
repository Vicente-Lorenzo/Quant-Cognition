import ast
import re
from pathlib import Path

import Library.App.V2 as V2
import Library.Web as Web
from Library.Utility.Path import inspect_module

_LIBRARY_ = inspect_module(V2.__file__) / "Assets"
_APPLICATION_ = inspect_module(Web.__file__) / "Assets"
_OWNED_ = ("Cron.js", "GateLive.js", "GateRuns.js", "GateSkip.js")
_VOCABULARY_ = ("Approving", "Reviewing", "Retrying", "crontab.guru")

def _requested_() -> set:
    wanted = set()
    for path in inspect_module(Web.__file__).rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute): continue
            if node.func.attr != "asset" or not node.args: continue
            if isinstance(node.args[0], ast.Constant): wanted.add(node.args[0].value)
    return wanted

def test_every_requested_asset_exists(application):
    requested = sorted(_requested_())
    assert len(requested) >= 12, f"only {len(requested)} asset requests were discovered"
    for name in requested:
        assert application.asset(name, url=False), f"{name} resolved empty"

def test_application_assets_are_the_quant_specific_callbacks():
    assert sorted(path.name for path in (_APPLICATION_ / "Callbacks").iterdir()) == sorted(_OWNED_)

def test_owned_callbacks_resolve_from_the_application_overlay(application):
    for name in _OWNED_:
        assert application.asset(f"Callbacks/{name}") == f"/_application/Callbacks/{name}"

def test_library_callbacks_still_resolve_from_the_library(application):
    for name in ("Callbacks/Gate.js", "Callbacks/Sheets.js", "Images/logo.png"):
        assert application.asset(name).startswith("/assets/")

def test_overlay_route_is_installed(application):
    routes = {str(rule) for rule in application.app.server.url_map.iter_rules()}
    assert "/_application/<path:filename>" in routes

def test_dash_still_serves_the_library_assets_folder(application):
    assert Path(application.app.config.assets_folder) == _LIBRARY_

def test_library_assets_carry_no_scheduler_vocabulary():
    offenders, scanned = [], 0
    for path in _LIBRARY_.rglob("*.js"):
        scanned += 1
        body = path.read_text(encoding="utf-8")
        offenders += [f"{path.name}:{word}" for word in _VOCABULARY_ if re.search(rf"\b{re.escape(word)}", body)]
    assert scanned >= 30, f"only {scanned} library scripts were scanned"
    assert not offenders, f"Quant Cognition vocabulary leaked into the generic App module: {offenders}"