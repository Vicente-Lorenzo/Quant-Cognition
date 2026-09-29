import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import Script.Environment.Update as Update

class _LogAPI:

    def __init__(self) -> None:
        self.warnings, self.errors = [], []

    def warning(self, content) -> None:
        self.warnings.append(content())

    def error(self, content) -> None:
        self.errors.append(content())

def _stage_(monkeypatch, tmp_path, *, live: dict, fresh: dict, passes: bool = True, stale: bool = True) -> tuple:
    calls, environment = [], tmp_path / "envs" / "Quant"
    environment.mkdir(parents=True)
    def _build_(successor, manifest):
        calls.append(("build", successor.name))
        successor.mkdir(exist_ok=True)
    def _verify_(successor):
        calls.append(("verify", successor.name))
        if not passes: raise RuntimeError("Tests failed on Quant.next · 1 failed")
        return "1833 passed"
    monkeypatch.setattr(Update, "find_environment", lambda: environment)
    monkeypatch.setattr(Update, "stale", lambda prefix, manifest: calls.append(("stale", prefix.name)) or stale)
    monkeypatch.setattr(Update, "discard", lambda prefix: calls.append(("discard", prefix.name)))
    monkeypatch.setattr(Update, "build", _build_)
    monkeypatch.setattr(Update, "listing", lambda prefix: [{"name": name, "version": version} for name, version in (fresh if prefix.name == "Quant.next" else live).items()])
    monkeypatch.setattr(Update, "verify", _verify_)
    return calls, environment

def _state_(environment: Path) -> dict:
    return json.loads((environment.with_name("Quant.next") / "Upgrade.json").read_text(encoding="utf-8"))

def test_nothing_is_built_while_nothing_would_move(monkeypatch, tmp_path):
    calls, environment = _stage_(monkeypatch, tmp_path, live={"numpy": "2.5.3"}, fresh={"numpy": "2.6.0"}, stale=False)
    assert Update.update_environment(_LogAPI()) == "Current"
    assert calls == [("stale", "Quant")]

def test_an_upgrade_is_built_beside_the_environment_and_validated_never_applied(monkeypatch, tmp_path):
    (calls, environment), log = _stage_(monkeypatch, tmp_path, live={"numpy": "2.5.3"}, fresh={"numpy": "2.6.0", "polars": "1.45.0"}), _LogAPI()
    assert Update.update_environment(log) == "Validated · 2 Moved"
    assert calls == [("stale", "Quant"), ("discard", "Quant.next"), ("build", "Quant.next"), ("verify", "Quant.next")]
    state = _state_(environment)
    assert state["State"] == "Validated" and state["Moved"] == ["numpy 2.5.3 → 2.6.0", "polars - → 1.45.0"] and state["Summary"] == "1833 passed"
    assert log.warnings[-1] == "Environment Upgrade: Validated · 2 Moved · 1833 passed · Applied at the next logon"
    assert sorted(path.name for path in environment.parent.iterdir()) == ["Quant", "Quant.next"]

def test_a_failing_build_is_kept_for_inspection_and_never_marked_valid(monkeypatch, tmp_path):
    calls, environment = _stage_(monkeypatch, tmp_path, live={"numpy": "2.5.3"}, fresh={"numpy": "2.6.0"}, passes=False)
    with pytest.raises(RuntimeError, match="Tests failed on Quant.next"): Update.update_environment(_LogAPI())
    assert _state_(environment)["State"] == "Failed" and environment.with_name("Quant.next").is_dir()

def test_a_successor_equal_to_the_environment_is_current(monkeypatch, tmp_path):
    calls, environment = _stage_(monkeypatch, tmp_path, live={"numpy": "2.6.0"}, fresh={"numpy": "2.6.0"})
    assert Update.update_environment(_LogAPI()) == "Current"
    assert _state_(environment)["State"] == "Current" and ("verify", "Quant.next") not in calls

def test_a_validated_successor_is_what_the_next_check_compares_against(monkeypatch, tmp_path):
    calls, environment = _stage_(monkeypatch, tmp_path, live={"numpy": "2.5.3"}, fresh={"numpy": "2.6.0"}, stale=False)
    successor = environment.with_name("Quant.next")
    successor.mkdir()
    (successor / "Upgrade.json").write_text(json.dumps({"State": "Validated", "Moved": ["numpy 2.5.3 → 2.6.0"]}), encoding="utf-8")
    assert Update.update_environment(_LogAPI()) == "Validated · Applied at the next logon"
    assert calls == [("stale", "Quant.next")]

def test_the_launchers_outcome_is_reported_once(monkeypatch, tmp_path):
    calls, environment = _stage_(monkeypatch, tmp_path, live={}, fresh={}, stale=False)
    successor = environment.with_name("Quant.next")
    successor.mkdir()
    (successor / "Upgrade.json").write_text(json.dumps({"State": "Restored", "Reason": "Previous environment restored · No module named numpy", "Reported": False}), encoding="utf-8")
    log = _LogAPI()
    Update.update_environment(log)
    Update.update_environment(log)
    assert log.errors == ["Environment Upgrade: Failed · Previous environment restored · No module named numpy"]

def test_the_state_line_names_current_next_and_previous(tmp_path):
    environment = tmp_path / "envs" / "Quant"
    environment.mkdir(parents=True)
    assert Update.describe(environment) == "Environment State: Current Quant · Next None · Previous None"
    environment.with_name("Quant.previous").mkdir()
    environment.with_name("Quant.next").mkdir()
    (environment.with_name("Quant.next") / "Upgrade.json").write_text(json.dumps({"State": "Validated", "Moved": ["a 1 → 2"]}), encoding="utf-8")
    assert Update.describe(environment) == "Environment State: Current Quant · Next Validated (1 Moved) · Previous Kept"

def test_the_manifest_declares_conda_names_without_versions_and_pip_without_options(tmp_path):
    manifest = tmp_path / "Quant.yml"
    manifest.write_text("name: Quant\ndependencies:\n    - python=3.12\n    - typing-extensions\n    - numpy >=2\n    - pip:\n        - --extra-index-url https://example.org\n        - torch\n", encoding="utf-8")
    assert Update.declared(manifest) == (["python", "typing-extensions", "numpy"], ["torch"])

def _gate_(monkeypatch, *, live: list, link: list, pip: list) -> list:
    calls = []
    monkeypatch.setattr(Update, "declared", lambda manifest: (["python", "numpy"], ["torch"]))
    monkeypatch.setattr(Update, "listing", lambda prefix: [{"name": name, "version": "1"} for name in live])
    monkeypatch.setattr(Update, "manage", lambda arguments: calls.append("conda") or SimpleNamespace(stdout=json.dumps({"actions": {"LINK": link}})))
    monkeypatch.setattr(Update, "execute", lambda command: calls.append("pip") or SimpleNamespace(stdout=json.dumps({"install": pip})))
    return calls

def test_the_gate_asks_the_cheapest_question_first(monkeypatch):
    calls = _gate_(monkeypatch, live=["python"], link=[], pip=[])
    assert Update.stale(Path("Quant"), Path("Quant.yml")) and calls == []
    calls = _gate_(monkeypatch, live=["python", "numpy"], link=[{"name": "numpy"}], pip=[])
    assert Update.stale(Path("Quant"), Path("Quant.yml")) and calls == ["conda"]
    calls = _gate_(monkeypatch, live=["python", "numpy"], link=[], pip=[{"metadata": {"name": "torch"}}])
    assert Update.stale(Path("Quant"), Path("Quant.yml")) and calls == ["conda", "pip"]
    calls = _gate_(monkeypatch, live=["python", "numpy"], link=[], pip=[])
    assert not Update.stale(Path("Quant"), Path("Quant.yml")) and calls == ["conda", "pip"]

def test_the_summary_is_the_pytest_line_not_the_last_log_line():
    output = "....\n3 failed, 1813 passed, 2 warnings in 130.65s (0:02:10)\n2026-09-26 - Info - Disconnect Operation: Disconnected\n"
    assert Update.summary(output) == "3 failed, 1813 passed, 2 warnings in 130.65s (0:02:10)"
    assert Update.summary("") == "No Summary"

def test_a_failure_is_named_by_its_error_lines_not_the_managers_boilerplate():
    result = SimpleNamespace(returncode=1, stdout="Linking x\n", stderr="critical libmamba Package nothing-0.0.0 not found\nIf you continue to meet this problem\nplease report it\n")
    assert Update.tail(result) == "critical libmamba Package nothing-0.0.0 not found"
    assert Update.tail(SimpleNamespace(returncode=2, stdout="", stderr="")) == "Exit 2"

def test_moved_names_every_package_that_changed_appeared_or_left():
    assert Update.moved({"a": "1", "b": "2", "c": "3"}, {"a": "1", "b": "3", "d": "4"}) == ["b 2 → 3", "c 3 → -", "d - → 4"]