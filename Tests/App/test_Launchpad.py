import pytest

from Library.App.V2 import LaunchpadAPI, LaunchpadPageAPI

class _FixedAPI_(LaunchpadAPI):

    _MATRIX_ = (4, 3)

class _ColumnsAPI_(LaunchpadAPI):

    _MATRIX_ = (6,)

def test_no_matrix_declares_no_style():
    assert LaunchpadAPI._matrix_() == {}

def test_the_framework_launchpad_is_automatic_by_default():
    assert LaunchpadPageAPI._MATRIX_ == ()
    assert LaunchpadPageAPI._matrix_() == {}

def test_columns_and_rows_are_both_emitted():
    assert _FixedAPI_._matrix_() == {"gridTemplateColumns": "repeat(4, minmax(0, 1fr))",
                                     "gridTemplateRows": "repeat(3, minmax(0, 1fr))"}

def test_columns_alone_leaves_rows_automatic():
    assert _ColumnsAPI_._matrix_() == {"gridTemplateColumns": "repeat(6, minmax(0, 1fr))"}

def test_the_matrix_reaches_the_rendered_grid():
    app = _build_()
    grid = _grid_(app._pages_["/"].content().build())
    assert grid.style == {"gridTemplateColumns": "repeat(3, minmax(0, 1fr))"}

def _build_():
    from Tests.App.Harness import HarnessAppAPI

    class _MatrixLaunchpadAPI_(LaunchpadPageAPI):
        _MATRIX_ = (3,)

    class _MatrixAppAPI_(HarnessAppAPI):
        Launchpad = _MatrixLaunchpadAPI_

    return _MatrixAppAPI_()

def _grid_(built):
    found = _find_(built)
    if found is None: pytest.fail("no launchpad grid was rendered")
    return found

def _find_(node):
    className = getattr(node, "className", None)
    if className and "app-launchpad-grid" in className: return node
    for child in _children_(node):
        found = _find_(child)
        if found is not None: return found
    return None

def _children_(node):
    if isinstance(node, (list, tuple)): return list(node)
    children = getattr(node, "children", None)
    if children is None: return []
    return children if isinstance(children, list) else [children]
