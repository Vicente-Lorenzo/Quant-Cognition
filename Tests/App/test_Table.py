from Library.App.V2.Lightweight.Table import TableAPI

_ROWS_ = [{"UID": "a", "Name": "Alpha", "Score": 1}, {"UID": "b", "Name": "Beta", "Score": 2}]

def test_page_defaults_match_table_defaults():
    assert TableAPI._columns_(TableAPI) == []
    assert TableAPI._rows_(TableAPI) == []
    assert TableAPI._markdown_columns_(TableAPI) == set()
    assert TableAPI._fingerprint_(TableAPI) is None

def test_page_editable_columns_default_to_empty():
    assert TableAPI._editable_columns_(TableAPI) == set()

def test_page_table_helper_builds_a_navigable_sheet():
    import json
    component = TableAPI.table({"name": "sub"}, "Deals", ["UID", "Name"], _ROWS_, base="/deals")
    payload = json.loads(component.encode())
    assert payload["navigation"] == {"base": "/deals", "key": "UID"}
    assert payload["sheets"][0]["name"] == "Deals"

def test_page_sheet_helper_delegates_to_the_spec():
    sheet = TableAPI.sheet("Rows", ["UID", "Name"], _ROWS_, markdown=("Name",))
    assert sheet.columns[1].markdown is True

def test_selected_reads_a_grid_state():
    assert TableAPI.selected({"selected": ["a", "b"]}) == ["a", "b"]
    assert TableAPI.selected({"rows": []}) == []

def test_selected_wraps_a_single_key_and_copies_a_list():
    assert TableAPI.selected("a") == ["a"]
    assert TableAPI.selected(("a", "b")) == ["a", "b"]
    assert TableAPI.selected(None) == []

def test_workspace_takes_a_title_and_editable_columns():
    payload = TableAPI.workspace("Rows", ["UID", "Name"], _ROWS_, title="Grid", editable=("Name",)).payload()
    assert payload["title"] == "Grid"
    assert [column.get("editable", False) for column in payload["sheets"][0]["columns"]] == [False, True]