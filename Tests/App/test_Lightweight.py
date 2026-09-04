from Library.Statistic.Workspace import WorkspaceAPI
from Library.App.V2.Lightweight.Lightweight import LightweightChartAPI, LightweightTableAPI

def test_chart_component_builds_host_and_carrier():
    built = LightweightChartAPI(id={"name": "chart"}, carrier={"name": "carrier"}, selection={"name": "state"}, workspace="demo", payload=WorkspaceAPI(title="W")).build()
    host = built[0]
    assert host.__dict__["data-workspace"] == "demo"
    assert host.__dict__["data-role"] == "chart"
    assert "lightweight" in host.className
    carrier, body = host.children
    assert carrier.type == "application/json" and "lightweight-payload" in carrier.className
    assert body.className == "lightweight-body"
    assert built[1].id == {"name": "state"}

def test_table_component_role_and_height_cap():
    built = LightweightTableAPI(id={"name": "grid"}, workspace="demo", height="40vh").build()
    host = built[0]
    assert host.__dict__["data-role"] == "table"
    assert host.style["maxHeight"] == "40vh"
    assert len(built) == 1

def test_component_without_payload_encodes_empty():
    assert LightweightChartAPI(id={"name": "c"}, workspace="w").encode() == "{}"

def test_component_injects_outbound_into_dict_payload():
    import json
    component = LightweightChartAPI(id={"name": "c"}, workspace="w", selection={"name": "s"}, payload={"panes": []})
    assert json.loads(component.encode())["outbound"] == {"name": "s"}

def test_component_injects_edition_into_dict_payload():
    import json
    component = LightweightTableAPI(id={"name": "g"}, workspace="w", edition={"name": "e"}, payload={"sheets": []})
    assert json.loads(component.encode())["edition"] == {"name": "e"}

def test_component_renders_the_edit_store():
    built = LightweightTableAPI(id={"name": "g"}, workspace="w", selection={"name": "s"}, edition={"name": "e"}).build()
    assert [element.id for element in built[1:]] == [{"name": "s"}, {"name": "e"}]