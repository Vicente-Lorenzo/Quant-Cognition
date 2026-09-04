import pytest

from Library.Web.App import WebAppAPI

@pytest.fixture(scope="session")
def application() -> WebAppAPI:
    return WebAppAPI(name="Quant Cognition", title="Quant Cognition", team="Team", contact="team@quant.test", host="127.0.0.1", port=8098)

@pytest.fixture(scope="session")
def owned(application) -> dict:
    import inspect
    from pathlib import Path
    from Library.Utility.Path import inspect_module
    root = inspect_module(inspect.getfile(WebAppAPI), resolve=True)
    return {endpoint: page for endpoint, page in application._pages_.items()
            if root in Path(inspect.getfile(type(page))).resolve().parents or Path(inspect.getfile(type(page))).resolve().parent == root}
