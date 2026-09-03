import pytest

from Library.App.V2 import AppAPI, RouterAPI
from Tests.App.Harness import build

@pytest.fixture(scope="module")
def app():
    return build()

def test_app_inherits_the_router():
    assert issubclass(AppAPI, RouterAPI)

def test_resolve_anchors_an_absolute_endpoint(app):
    assert app.resolve(path="/alpha", relative=False, footer=True) == "/alpha/"

def test_resolve_omits_the_footer_when_asked(app):
    assert app.resolve(path="/alpha", relative=False, footer=False) == "/alpha"

def test_anchorize_never_trails_a_separator(app):
    assert not app.anchorize(path="/alpha", relative=False).endswith("/")

def test_endpointize_always_trails_a_separator(app):
    assert app.endpointize(path="/alpha", relative=False).endswith("/")

def test_locate_finds_a_registered_page(app):
    endpoint, page = app.locate(endpoint=app.endpointize(path="/alpha", relative=True))
    assert page is not None and page.button == "Alpha"

def test_locate_misses_an_unregistered_path(app):
    endpoint, page = app.locate(endpoint="/nowhere/")
    assert page is None and endpoint == "/nowhere/"

def test_locate_falls_back_to_a_parametric_page(app):
    endpoint, page = app.locate(endpoint=app.endpointize(path="/alpha/abc123", relative=True))
    assert page is not None and page.button == "Alpha Detail"

def test_parametric_page_is_flagged_parametric(app):
    _, page = app.locate(endpoint=app.endpointize(path="/alpha/abc123", relative=True))
    assert page._parametric_ is True

def test_parametric_registry_holds_the_anchor(app):
    assert any("alpha" in key for key in app._parametrics_)

def test_an_exact_match_wins_over_the_parametric_fallback(app):
    _, page = app.locate(endpoint=app.endpointize(path="/alpha", relative=True))
    assert page.button == "Alpha"

def test_redirect_follows_a_declared_target(app):
    endpoint, page = app.redirect(endpoint=app.endpointize(path="/gamma", relative=True))
    assert page is not None and page.button == "Alpha"

def test_redirect_leaves_a_plain_page_alone(app):
    endpoint, page = app.redirect(endpoint=app.endpointize(path="/beta", relative=True))
    assert page.button == "Beta"

def test_redirect_of_an_unknown_path_yields_no_page(app):
    _, page = app.redirect(endpoint="/nowhere/")
    assert page is None

def test_route_callback_paints_a_known_page(app):
    result = app._global_async_update_location_callback_(app.endpointize(path="/alpha", relative=True), None, None, None, None, None)
    assert isinstance(result, tuple) and len(result) == 10

def test_route_callback_builds_the_navigation(app):
    result = app._global_async_update_location_callback_(app.endpointize(path="/beta", relative=True), None, None, None, None, None)
    assert result[2] is not None

def test_route_callback_survives_an_unknown_path(app):
    result = app._global_async_update_location_callback_("/nowhere/", None, None, None, None, None)
    assert isinstance(result, tuple) and len(result) == 10

def test_route_callback_survives_a_missing_pathname(app):
    assert isinstance(app._global_async_update_location_callback_(None, None, None, None, None, None), tuple)

def test_route_callback_renders_a_parametric_page(app):
    result = app._global_async_update_location_callback_(app.endpointize(path="/alpha/xyz", relative=True), None, None, None, None, None)
    assert isinstance(result, tuple) and len(result) == 10

def test_route_callback_is_declared_a_callback():
    assert getattr(RouterAPI._global_async_update_location_callback_, "callback", False) is True

def test_index_registers_a_page_under_an_endpoint(app):
    page = app.locate(endpoint=app.endpointize(path="/beta", relative=True))[1]
    app.index(endpoint="/spare/", page=page)
    assert app.locate(endpoint="/spare/")[1] is page