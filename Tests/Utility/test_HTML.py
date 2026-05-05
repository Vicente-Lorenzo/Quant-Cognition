import dash.html as html
from Library.Utility.HTML import htmlize, stylize
def test_text():
    assert htmlize("hello") == "hello"
def test_number():
    assert htmlize(5) == "5"
def test_list():
    assert htmlize(["a", "b"]) == "ab"
def test_basic_component():
    div = html.Div("hi")
    assert htmlize(div) == "<div>hi</div>"
def test_component_with_props():
    div = html.Div("x", id="foo", className="bar")
    assert htmlize(div) == '<div id="foo" class="bar">x</div>'
def test_nested():
    comp = html.Div([html.H1("A"), html.P("B")])
    assert htmlize(comp) == "<div><h1>A</h1><p>B</p></div>"
def test_none_child():
    div = html.Div(None)
    assert htmlize(div) == "<div></div>"
def test_stylize():
    div = html.Div("x", id="a")
    assert stylize(div) == ' id="a"'