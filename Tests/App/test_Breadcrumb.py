from Library.App.V2.Breadcrumb import BreadcrumbAPI, CrumbAPI

def test_crumb_resolves_a_pair():
    crumb = CrumbAPI.resolve(("Workflows", "/scheduler/workflows"))
    assert (crumb.label, crumb.href) == ("Workflows", "/scheduler/workflows")

def test_crumb_resolves_a_bare_label():
    assert CrumbAPI.resolve("Runs").href is None

def test_crumb_passes_an_instance_through():
    crumb = CrumbAPI(label="Tasks", href="/t")
    assert CrumbAPI.resolve(crumb) is crumb

def test_trail_drops_missing_entries():
    trail = BreadcrumbAPI(trail=[CrumbAPI(label="A"), None, ("B", "/b")]).crumbs()
    assert [entry.label for entry in trail] == ["A", "B"]

def test_build_separates_every_pair():
    built = BreadcrumbAPI(trail=[("A", "/a"), ("B", "/b"), "C"]).build()
    labels = [child.children for child in built[0].children]
    assert labels == ["A", "›", "B", "›", "C"]

def test_build_marks_the_last_crumb_current():
    built = BreadcrumbAPI(trail=[("A", "/a"), "C"]).build()
    assert built[0].children[-1].className == "crumb crumb-current"

def test_build_never_links_the_last_crumb():
    built = BreadcrumbAPI(trail=[("A", "/a"), ("B", "/b")]).build()
    assert not hasattr(built[0].children[-1], "href")

def test_build_links_the_earlier_crumbs():
    built = BreadcrumbAPI(trail=[("A", "/a"), "B"]).build()
    assert built[0].children[0].href == "/a"

def test_single_crumb_needs_no_separator():
    built = BreadcrumbAPI(trail=["Only"]).build()
    assert len(built[0].children) == 1

def test_separator_is_configurable():
    built = BreadcrumbAPI(trail=["A", "B"], separator="/").build()
    assert built[0].children[1].children == "/"