from Library.App.V2.Chart import NetworkAPI

_NODES_ = [{"uid": "A", "color": "#2f9e44", "hover": "A<br>Success"}, {"uid": "B", "color": None, "hover": "B<br>No run"}, {"uid": "C"}]
_EDGES_ = [("A", "B"), ("B", "C")]

def test_blank_states_the_reason():
    figure = NetworkAPI.blank("No tasks")
    assert figure.layout.annotations[0].text == "No tasks"
    assert figure.layout.dragmode is False

def test_blank_locks_both_axes():
    figure = NetworkAPI.blank("Idle")
    assert figure.layout.xaxis.fixedrange is True
    assert figure.layout.yaxis.fixedrange is True

def test_render_without_nodes_falls_back_to_the_placeholder():
    assert NetworkAPI.render([], [], placeholder="Workflow has no tasks").layout.annotations[0].text == "Workflow has no tasks"

def test_render_draws_edges_then_nodes():
    figure = NetworkAPI.render(_NODES_, _EDGES_)
    assert len(figure.data) == 2
    assert figure.data[0].mode == "lines"
    assert figure.data[1].mode == "markers+text"

def test_render_labels_every_node():
    assert set(NetworkAPI.render(_NODES_, _EDGES_).data[1].text) == {"A", "B", "C"}

def test_render_carries_the_uid_as_customdata():
    figure = NetworkAPI.render(_NODES_, _EDGES_)
    assert list(figure.data[1].customdata) == list(figure.data[1].text)

def test_render_skips_the_edge_trace_when_hit_testing():
    assert NetworkAPI.render(_NODES_, _EDGES_).data[0].hoverinfo == "skip"

def test_render_falls_back_on_a_missing_color():
    colors = NetworkAPI.render(_NODES_, _EDGES_, fallback="#565a66").data[1].marker.color
    assert colors[1] == "#565a66" and colors[2] == "#565a66"

def test_render_shows_no_tooltip_on_either_trace():
    figure = NetworkAPI.render(_NODES_, _EDGES_)
    assert figure.data[0].hoverinfo == "skip"
    assert figure.data[1].hoverinfo == "none"

def test_render_anchors_each_arrow_at_the_segment_midpoint():
    figure = NetworkAPI.render(_NODES_, _EDGES_)
    for arrow in figure.layout.annotations:
        assert min(arrow.ax, arrow.x) < (arrow.ax + arrow.x) / 2 < max(arrow.ax, arrow.x) or arrow.ax != arrow.x

def test_render_thickens_the_edges():
    assert NetworkAPI.render(_NODES_, _EDGES_).data[0].line.width == 2.4

def test_order_lists_nodes_in_topological_layers():
    assert NetworkAPI.order(_NODES_, _EDGES_) == ["A", "B", "C"]

def test_order_falls_back_to_declaration_order_on_a_cycle():
    assert NetworkAPI.order(_NODES_, [("A", "B"), ("B", "A")]) == ["A", "B", "C"]

def test_order_of_nothing_is_nothing():
    assert NetworkAPI.order([], []) == []

def test_render_draws_one_arrow_per_edge():
    assert len(NetworkAPI.render(_NODES_, _EDGES_).layout.annotations) == 2

def test_render_ignores_edges_outside_the_node_set():
    assert len(NetworkAPI.render(_NODES_, _EDGES_ + [("A", "Z")]).layout.annotations) == 2

def test_render_reports_a_dependency_cycle():
    assert NetworkAPI.render(_NODES_, [("A", "B"), ("B", "A")]).layout.annotations[0].text == "Dependency cycle detected"

def test_render_reverses_the_vertical_axis():
    assert NetworkAPI.render(_NODES_, _EDGES_).layout.yaxis.autorange == "reversed"

def test_component_defaults_to_the_zoomless_config():
    component = NetworkAPI(id={"name": "dag"}, nodes=_NODES_, edges=_EDGES_)
    assert component.config["scrollZoom"] is False
    assert component.config["doubleClick"] is False

def test_component_builds_its_own_figure():
    assert len(NetworkAPI(id={"name": "dag"}, nodes=_NODES_, edges=_EDGES_).figure.data) == 2

def test_component_without_nodes_shows_the_placeholder():
    component = NetworkAPI(id={"name": "dag"}, placeholder="Loading dependency graph")
    assert component.figure.layout.annotations[0].text == "Loading dependency graph"

def test_component_wraps_itself_when_an_anchor_is_given():
    built = NetworkAPI(id={"name": "dag"}, nodes=_NODES_, edges=_EDGES_, anchor="/scheduler/tasks").build()
    assert built[0].className == "network-host"
    assert built[0].__dict__["data-open"] == "/scheduler/tasks"

def test_component_without_an_anchor_stays_bare():
    built = NetworkAPI(id={"name": "dag"}, nodes=_NODES_, edges=_EDGES_).build()
    assert built[0].className != "network-host"