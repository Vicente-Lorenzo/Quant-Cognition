import re

import pytest

import Library.App.V2 as V2
from Library.System.Space import AUTOMATIC
from Library.Utility.Parameter import SEPARATOR
from Library.Utility.Path import inspect_module
from Library.Utility.Range import RangeAPI

_GRID_ = inspect_module(V2.__file__) / "Assets" / "Scripts" / "Grid.js"

def _grid_() -> str:
    if not _GRID_.is_file(): pytest.skip("Grid.js not present")
    return _GRID_.read_text(encoding="utf-8")

def _literal_(pattern: str) -> str:
    found = re.search(pattern, _grid_())
    assert found is not None, f"Grid.js no longer declares {pattern}"
    return found.group(1)

def test_range_grammar_matches_the_engine():
    assert _literal_(r"var RANGE = /(.*)/;") == RangeAPI._PATTERN_.pattern

def test_separator_matches_the_engine():
    assert _literal_(r'var SEPARATOR = "(.*)";') == SEPARATOR

def test_auto_marker_matches_the_engine():
    assert _literal_(r'var MODES = \["([^"]*)"') == AUTOMATIC

def test_declared_modes_are_the_three_editor_kinds():
    assert re.findall(r'"([^"]*)"', _literal_(r"var MODES = \[(.*)\];")) == [AUTOMATIC, "Range", "List"]