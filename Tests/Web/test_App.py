from datetime import datetime

from Library.App.V2.Page.Settings import SettingsPageAPI
from Library.Auth import RoleAPI
from Library.Web.Core.Status import StatusAPI
from Library.Web.Scheduler.Workflow import SchedulerWorkflowAPI

_ACCESS_ = {"/trading": RoleAPI.Administrator, "/framework/database": RoleAPI.Moderator,
            "/framework": RoleAPI.Viewer, "/framework/hierarchy": RoleAPI.Viewer,
            "/framework/credential": RoleAPI.Viewer}

def test_every_declared_page_is_registered(application):
    assert len(application._pages_) == 26

def test_endpoints_are_unique(application):
    assert len(set(application._pages_)) == len(application._pages_)

def test_every_detail_page_is_parametric(application):
    detail = [endpoint for endpoint in application._pages_ if ":uid" in endpoint]
    assert len(detail) == 4
    for endpoint in detail:
        parent = endpoint.rsplit(":uid", 1)[0]
        assert parent in application._parametrics_, f"{endpoint} has no parametric parent"

def test_sections_carry_their_children(owned):
    for anchor in ("/research", "/strategy", "/scheduler", "/framework"):
        children = [endpoint for endpoint in owned if endpoint.startswith(anchor + "/")]
        assert children, f"{anchor} has no child page"

def test_access_levels_are_declared_as_intended(application):
    for endpoint, role in _ACCESS_.items():
        page = next((page for key, page in application._pages_.items() if key.rstrip("/") == endpoint), None)
        assert page is not None, f"{endpoint} is not registered"
        assert page.access is role, f"{endpoint} is {page.access} not {role}"

def test_the_root_launchpad_carries_no_access_gate(owned):
    assert owned["/"].access is None

def test_every_other_owned_page_is_editor(owned):
    assert len(owned) == 24, f"the owned-page fixture found {len(owned)}"
    for endpoint, page in owned.items():
        if endpoint == "/" or endpoint.rstrip("/") in _ACCESS_: continue
        assert page.access is RoleAPI.Editor, f"{endpoint} is {page.access}"

def test_the_root_launchpad_is_a_four_by_two_matrix(application):
    root = application._pages_["/"]
    assert type(root).__name__ == "WebLaunchpadPageAPI"
    assert root._matrix_() == {"gridTemplateColumns": "repeat(4, minmax(0, 1fr))",
                              "gridTemplateRows": "repeat(2, minmax(0, 1fr))"}

def test_section_launchpads_stay_automatic(application):
    for endpoint in ("/research/", "/strategy/", "/scheduler/", "/framework/"):
        assert application._pages_[endpoint]._matrix_() == {}, f"{endpoint} pins its grid"

def test_settings_offer_a_display_zone_that_defaults_to_the_browser(application):
    page = next(page for page in application._pages_.values() if isinstance(page, SettingsPageAPI))
    dropdown = page._zone_()
    assert dropdown.value == "Browser" and dropdown.persistence_type == "local"
    assert [option["value"] for option in dropdown.options[:2]] == ["Browser", "UTC"]

def test_workflow_zone_field_writes_the_zone_column():
    field = SchedulerWorkflowAPI._FIELD_["zone"]
    assert field.column == "Zone" and field.write("") is None
    assert "Zone" in SchedulerWorkflowAPI._WORKFLOW_COLUMNS_

def test_detail_stamps_carry_their_utc_value():
    stamp = StatusAPI._stamp_(datetime(2026, 7, 1, 13, 0, 5))
    assert stamp.children == "2026-07-01 13:00:05"
    assert getattr(stamp, "data-utc") == "2026-07-01 13:00:05"
    assert StatusAPI._stamp_(None) is None