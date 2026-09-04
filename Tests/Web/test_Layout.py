import importlib
import inspect
from pathlib import Path

import pytest

import Library.Web as Web
from Library.Utility.Path import inspect_module

_PACKAGES_ = ("Core", "Trading", "Research", "Strategy", "Scheduler", "Framework", "Service")
_ROOT_ = inspect_module(Web.__file__)

def test_every_page_lives_under_its_father_root(application):
    checked = 0
    for endpoint, page in sorted(application._pages_.items()):
        source = Path(inspect.getfile(type(page))).resolve()
        if _ROOT_ not in source.parents: continue
        father = endpoint.strip("/").split("/")[0]
        expected = _ROOT_ if not father else _ROOT_ / father.capitalize()
        assert source.parent == expected, f"{endpoint} is declared in {source.parent.name}"
        checked += 1
    assert checked == 23, f"only {checked} owned pages were checked"

def test_declared_packages_all_exist():
    for name in _PACKAGES_:
        assert (_ROOT_ / name / "__init__.py").is_file(), f"Library/Web/{name} is not a package"

def test_only_the_composition_root_sits_at_the_top(application):
    assert sorted(path.name for path in _ROOT_.glob("*.py")) == ["App.py", "Launchpad.py", "__init__.py"]

@pytest.mark.parametrize("name", _PACKAGES_)
def test_every_package_imports_cleanly_on_its_own(name):
    module = importlib.import_module(f"Library.Web.{name}")
    assert module.__all__, f"Library.Web.{name} exports nothing"
    for export in module.__all__:
        assert hasattr(module, export), f"Library.Web.{name}.{export} is unresolvable"

def test_the_package_surface_resolves():
    for name in Web.__all__:
        assert hasattr(Web, name), f"Library.Web.{name} is unresolvable"

def test_the_parent_imports_through_its_packages():
    source = (_ROOT_ / "__init__.py").read_text(encoding="utf-8")
    leaked = [name for name in _PACKAGES_ if f"from Library.Web.{name}." in source]
    assert not leaked, f"the parent reaches past its packages into {leaked}"

def test_service_stays_out_of_the_library_surface():
    source = (_ROOT_ / "__init__.py").read_text(encoding="utf-8")
    assert "Library.Web.Service" not in source
