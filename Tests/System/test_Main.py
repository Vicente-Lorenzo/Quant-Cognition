import ast
import inspect
from pathlib import Path

import pytest

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

class _Rung_:

    def __init__(self, uid: str) -> None:
        self.UID = uid

@pytest.mark.parametrize("spelling", ["Hour", "HOUR", "hourly", "H", "1H", "H1", "60"])
def test_every_spelling_of_a_timeframe_lands_on_one_ladder_scope(spelling):
    from Library.System.Main import scope
    rungs = scope(_Rung_("Spotware(cTrader)"), _Rung_("Forex(Major)"), _Rung_("EURUSD"), _Rung_(spelling))
    assert rungs == ("Spotware(cTrader)", "Forex(Major)", "EURUSD", "H1")

def test_distinct_timeframes_get_distinct_scopes():
    from Library.System.Main import scope
    made = {scope(_Rung_("P"), _Rung_("C"), _Rung_("T"), _Rung_(uid))[-1] for uid in ("Hour", "Daily", "H4", "M15", "Monthly")}
    assert made == {"H1", "D1", "H4", "M15", "MN1"}