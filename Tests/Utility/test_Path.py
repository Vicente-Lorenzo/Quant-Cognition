import tempfile
from pathlib import Path

from Library.Utility.Path import inspect_application, inspect_cached, inspect_destination, inspect_persistent, inspect_root, inspect_temporary

def test_application_is_the_project_root_name():
    assert inspect_application() == Path(__file__).resolve().parents[2].name

def test_every_tier_is_namespaced_by_the_application():
    application = inspect_application()
    assert application in inspect_temporary().parts
    assert application in inspect_persistent().parts
    assert application in inspect_cached().parts

def test_no_tier_hardcodes_a_product_name():
    for tier in (inspect_temporary(), inspect_persistent(), inspect_cached()):
        assert "Quant" not in str(tier)

def test_every_tier_shares_one_application_root():
    assert inspect_temporary("Runs") == inspect_root() / "Temp" / "Runs"
    assert inspect_persistent("Runs") == inspect_root() / "Data" / "Runs"
    assert inspect_cached("Preload") == inspect_root() / "Cache" / "Preload"

def test_no_tier_depends_on_the_operating_system_temporary_folder():
    system = Path(tempfile.gettempdir()).resolve()
    for tier in (inspect_temporary(), inspect_persistent(), inspect_cached()):
        resolved = tier.resolve()
        assert resolved != system and system not in resolved.parents

def test_cache_is_separate_from_persisted():
    assert inspect_cached().resolve() != inspect_persistent().resolve()

def test_folders_append_in_order():
    assert inspect_cached("Preload", "EURUSD").parts[-2:] == ("Preload", "EURUSD")

def test_destination_still_resolves_against_the_temporary_tier():
    assert inspect_destination(True, "Exports") == inspect_temporary("Exports")
    assert inspect_destination(False, "Exports") is None
    assert inspect_destination("D:/Somewhere", "Exports") == Path("D:/Somewhere")