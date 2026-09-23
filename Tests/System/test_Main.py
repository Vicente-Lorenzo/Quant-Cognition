import ast
import inspect
import json
from pathlib import Path

import pytest

from Library.Logging import LoggingAPI
from Library.System import Main
from Library.System.System import SystemAPI

SOURCE = Path(inspect.getfile(Main))

def constructed() -> dict:
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    builder = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == "_system_")
    calls = {}
    for node in ast.walk(builder):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name): continue
        if not node.func.id.endswith("API"): continue
        calls[node.func.id] = {keyword.arg for keyword in node.keywords if keyword.arg is not None}
    return calls

def resolve(name: str):
    target = getattr(Main, name, None)
    return target if inspect.isclass(target) else None

def test_main_builds_every_system():
    assert constructed(), "no system constructors found in _system_"

@pytest.mark.parametrize("name", sorted(constructed()))
def test_every_argument_is_accepted(name):
    system = resolve(name)
    if system is None: pytest.skip(f"{name} is not importable from Main")
    accepted = set(inspect.signature(system.__init__).parameters) - {"self"}
    passed = constructed()[name]
    assert not (passed - accepted), f"{name} is handed {sorted(passed - accepted)} by Main._system_ but does not accept it"

@pytest.mark.parametrize("name", sorted(constructed()))
def test_every_system_forwards_the_shared_surface(name):
    system = resolve(name)
    if system is None: pytest.skip(f"{name} is not importable from Main")
    if system is SystemAPI: pytest.skip("SystemAPI is the base itself")
    shared = set(inspect.signature(SystemAPI.__init__).parameters) - {"self"}
    accepted = set(inspect.signature(system.__init__).parameters) - {"self"}
    body = inspect.getsource(system.__init__)
    forwarded = body.split("super().__init__", 1)[-1]
    for parameter in sorted(shared & accepted):
        assert f"{parameter}=" in forwarded, f"{name} accepts {parameter} but never forwards it to SystemAPI"

@pytest.mark.parametrize("name", ["BacktestingAPI", "OptimizationAPI", "LearningAPI"])
def test_every_offline_system_takes_the_risk_free_rate_and_the_benchmark(name):
    assert {"risk_free", "benchmark"} <= constructed()[name]

class _Rung_:

    def __init__(self, uid: str) -> None:
        self.UID = uid

@pytest.mark.parametrize("spelling", ["Hour", "HOUR", "hourly", "H", "1H", "H1", "60"])
def test_every_spelling_of_a_timeframe_lands_on_one_ladder_scope(spelling):
    from Library.System.Main import _scope_ as scope
    rungs = scope(_Rung_("Spotware(cTrader)"), _Rung_("Forex(Major)"), _Rung_("EURUSD"), _Rung_(spelling))
    assert rungs == ("Spotware(cTrader)", "Forex(Major)", "EURUSD", "H1")

def test_distinct_timeframes_get_distinct_scopes():
    from Library.System.Main import _scope_ as scope
    made = {scope(_Rung_("P"), _Rung_("C"), _Rung_("T"), _Rung_(uid))[-1] for uid in ("Hour", "Daily", "H4", "M15", "Monthly")}
    assert made == {"H1", "D1", "H4", "M15", "MN1"}

class _Args_:

    def __init__(self, **fields):
        self.system, self.strategy, self.provider = "Simulation", "Trend", "Spotware"
        self.ticker, self.timeframe, self.description, self.user = "EURUSD", "Hour", None, None
        for name, value in fields.items(): setattr(self, name, value)

def test_snapshot_writes_the_manifest_without_a_period(tmp_path):
    from Library.System.Main import _snapshot_ as snapshot
    snapshot(tmp_path, _Args_(description="Golden 1"), None, LoggingAPI())
    manifest = json.loads((tmp_path / "Run.json").read_text(encoding="utf-8"))
    assert manifest["System"] == "Simulation"
    assert manifest["Description"] == "Golden 1"
    assert "Start" not in manifest and "Stop" not in manifest and "User" not in manifest

def test_snapshot_records_who_the_run_acts_as(tmp_path):
    from Library.System.Main import _snapshot_ as snapshot
    snapshot(tmp_path, _Args_(user="owner@test.com"), None, LoggingAPI())
    assert json.loads((tmp_path / "Run.json").read_text(encoding="utf-8"))["User"] == "owner@test.com"

def test_snapshot_keeps_the_period_when_one_is_supplied(tmp_path):
    from Library.System.Main import _snapshot_ as snapshot
    snapshot(tmp_path, _Args_(system="Backtesting", start="2023-01-01", stop="2024-01-01"), None, LoggingAPI())
    manifest = json.loads((tmp_path / "Run.json").read_text(encoding="utf-8"))
    assert manifest["Start"] == "2023-01-01" and manifest["Stop"] == "2024-01-01"

@pytest.mark.parametrize("system", ["Backtesting", "Optimization", "Learning"])
def test_every_offline_system_accepts_pinned_parameters(system, monkeypatch):
    monkeypatch.setattr("sys.argv", ["Main.py", system, "--start", "2020-01-01", "--stop", "2021-01-01", "--parameters", "Pinned.yml"])
    assert Main._parse_().parameters == "Pinned.yml"

def test_realtime_systems_do_not_take_pinned_parameters(monkeypatch):
    monkeypatch.setattr("sys.argv", ["Main.py", "Simulation", "--parameters", "Pinned.yml"])
    with pytest.raises(SystemExit):
        Main._parse_()

def test_parameters_default_to_the_ladder_when_nothing_is_pinned(monkeypatch):
    monkeypatch.setattr("sys.argv", ["Main.py", "Backtesting", "--start", "2020-01-01", "--stop", "2021-01-01"])
    assert Main._parse_().parameters is Main.MISSING

class _Ladder_:

    def parameterize(self, strategy, kind, *rungs):
        return "Ladder", ["Defaults"]

    def pin(self, strategy, kind, source, target):
        return ("Pinned", source, target), ["Defaults", source]

def test_a_pinned_path_bypasses_the_ladder_and_targets_the_run_folder(tmp_path):
    trails = {}
    pinned = Main._parameters_(_Ladder_(), None, (), trails, tmp_path, "Backtesting", "Pinned.yml")
    assert pinned == ("Pinned", "Pinned.yml", tmp_path / "Input" / "Parameters.yml")
    assert trails["Backtesting"] == ["Defaults", "Pinned.yml"]
    assert Main._parameters_(_Ladder_(), None, (), trails, tmp_path, "Optimization") == "Ladder"

@pytest.mark.parametrize("system", ["Backtesting", "Optimization", "Learning"])
@pytest.mark.parametrize("given", [[], ["--start", "2020-01-01"], ["--stop", "2021-01-01"]])
def test_every_offline_system_requires_both_ends_of_the_period(system, given, monkeypatch):
    monkeypatch.setattr("sys.argv", ["Main.py", system, *given])
    with pytest.raises(SystemExit):
        Main._parse_()

def test_snapshot_records_a_command_that_splits_back_into_the_same_arguments(tmp_path, monkeypatch):
    from Library.System.Main import _snapshot_ as snapshot
    from Library.Utility.Runtime import split_arguments
    arguments = ["Backtesting", "--description", "Golden with spaces", "--run", str(tmp_path / "Offline Golden 1")]
    monkeypatch.setattr("sys.argv", ["Main.py", *arguments])
    snapshot(tmp_path, _Args_(system="Backtesting"), None, LoggingAPI())
    assert split_arguments(json.loads((tmp_path / "Run.json").read_text(encoding="utf-8"))["Command"]) == arguments

@pytest.mark.parametrize("system", ["Backtesting", "Optimization", "Learning"])
def test_every_offline_system_accepts_a_pinned_contract(system, monkeypatch):
    monkeypatch.setattr("sys.argv", ["Main.py", system, "--start", "2020-01-01", "--stop", "2021-01-01", "--contract", "Contract.yml"])
    assert Main._parse_().contract == "Contract.yml"

def test_realtime_systems_take_their_contract_from_the_wire(monkeypatch):
    monkeypatch.setattr("sys.argv", ["Main.py", "Simulation", "--contract", "Contract.yml"])
    with pytest.raises(SystemExit):
        Main._parse_()

def test_a_pinned_contract_replaces_the_stored_terms_in_memory(tmp_path):
    from types import SimpleNamespace
    from Library.Universe.Contract import ContractAPI
    from Library.Universe.Ticker import ContractType
    from Library.Utility.IO import write_yaml
    stored = ContractAPI(Ticker="EURUSD", Provider="Spotware(cTrader)", Type=ContractType.Spot, SwapLong=-2.445)
    pinned = ContractAPI(Ticker="EURUSD", Provider="Spotware(cTrader)", Type=ContractType.Spot, SwapLong=-9.0)
    write_yaml(tmp_path / "Contract.yml", pinned.snapshot(), safe=False)
    security = SimpleNamespace(Contract=stored, Ticker=SimpleNamespace(UID="EURUSD"))
    Main._contract_(security, Main.MISSING)
    assert stored.SwapLong == -2.445
    Main._contract_(security, str(tmp_path / "Contract.yml"))
    assert stored.SwapLong == -9.0 and stored._db_ is None

def test_snapshot_records_where_the_contract_came_from(tmp_path):
    from Library.System.Main import _snapshot_ as snapshot
    snapshot(tmp_path, _Args_(system="Backtesting", contract="Pinned/Contract.yml"), None, LoggingAPI())
    assert json.loads((tmp_path / "Run.json").read_text(encoding="utf-8"))["Contract"] == "Pinned/Contract.yml"
    snapshot(tmp_path, _Args_(system="Simulation"), None, LoggingAPI())
    assert "Contract" not in json.loads((tmp_path / "Run.json").read_text(encoding="utf-8"))