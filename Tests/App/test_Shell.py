import pytest

from Library.App.V2 import AppAPI, ShellAPI
from Tests.App.Harness import build

@pytest.fixture(scope="module")
def app():
    return build()

def classes(node) -> str:
    return str(getattr(node, "className", "") or "")

def walk(node):
    yield node
    children = getattr(node, "children", None)
    if children is None: return
    for child in (children if isinstance(children, (list, tuple)) else [children]):
        if hasattr(child, "children") or hasattr(child, "className"): yield from walk(child)

def find(node, token: str):
    return [entry for entry in walk(node) if token in classes(entry)]

def test_app_inherits_the_shell():
    assert issubclass(AppAPI, ShellAPI)

def test_header_carries_the_brand_nav_and_menu(app):
    header = app.__init_header_layout__()
    assert find(header, "app-brand") and find(header, "app-nav") and find(header, "app-menu")

def test_header_carries_the_navigation_toggle(app):
    assert find(app.__init_header_layout__(), "app-nav-toggle")

def test_navigation_toggle_precedes_the_account_menu(app):
    order = [classes(entry) for entry in walk(app.__init_header_layout__())]
    toggle = next(index for index, name in enumerate(order) if "app-nav-toggle" in name)
    menu = next(index for index, name in enumerate(order) if "app-menu" in name)
    assert toggle < menu

def test_menu_offers_the_account_actions(app):
    labels = [str(getattr(entry, "children", "")) for entry in walk(app.__init_menu_layout__()[0])]
    assert any("Theme" in label for label in labels)

def test_footer_has_three_regions(app):
    footer = app.__init_footer_layout__()
    assert find(footer, "left") and find(footer, "center") and find(footer, "right")

def test_footer_shows_a_motto(app):
    assert find(app.__init_footer_layout__(), "app-motto")

def test_body_holds_the_sidebar_and_content(app):
    body = app.__init_body_layout__()
    assert find(body, "sidebar") and find(body, "content")

def test_hidden_layout_is_a_single_host(app):
    assert "app-hidden" in classes(app.__init_hidden_layout__())

def test_modal_layout_builds(app):
    assert app.__init_modal_layout__() is not None

def test_default_layout_seeds_every_fallback(app):
    app.__init_default_layout__()
    for name in ("GLOBAL_NOT_FOUND_LAYOUT", "GLOBAL_LOADING_LAYOUT", "GLOBAL_MAINTENANCE_LAYOUT",
                 "GLOBAL_DEVELOPMENT_LAYOUT", "GLOBAL_FORBIDDEN_LAYOUT"):
        assert getattr(app, name) is not None

def test_layout_composes_the_whole_shell(app):
    names = " ".join(classes(entry) for entry in walk(app.app.layout))
    assert "app-header" in names and "app-body" in names and "app-footer" in names

def test_navigation_is_built_for_every_page(app):
    app._init_navigation_()
    assert all(page._navigation_ is not None for page in app._pages_.values())

def test_navigation_is_populated_for_a_page_with_siblings(app):
    app._init_navigation_()
    _, page = app.locate(endpoint=app.endpointize(path="/alpha", relative=True))
    assert len(page._navigation_) > 0

def test_navigation_is_rebuilt_idempotently(app):
    app._init_navigation_()
    _, page = app.locate(endpoint=app.endpointize(path="/alpha", relative=True))
    before = len(page._navigation_)
    app._init_navigation_()
    assert len(page._navigation_) == before

def test_navigation_toggle_callback_is_clientside():
    assert getattr(ShellAPI._navigation_toggle_callback_, "js", False) is True

def test_navigation_toggle_callback_returns_its_asset(app):
    assert app._navigation_toggle_callback_().strip().startswith("(function")

def test_tip_builds_a_tooltip(app):
    assert app._tip_(app.GLOBAL_BRAND_ID, "hello") is not None

def test_label_pairs_an_icon_with_the_button(app):
    _, page = app.locate(endpoint=app.endpointize(path="/alpha", relative=True))
    assert isinstance(app._label_(page), list)

def test_label_of_an_iconless_page_is_bare_text(app):
    _, page = app.locate(endpoint=app.endpointize(path="/gamma", relative=True))
    assert app._label_(page) == page.button