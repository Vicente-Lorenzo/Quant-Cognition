from Library.Auth import RoleAPI

_ACCESS_ = {"/trading": RoleAPI.Administrator, "/framework/database": RoleAPI.Moderator,
            "/framework": RoleAPI.Viewer, "/framework/hierarchy": RoleAPI.Viewer}

def test_every_declared_page_is_registered(application):
    assert len(application._pages_) == 25

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
    assert len(owned) == 23, f"the owned-page fixture found {len(owned)}"
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