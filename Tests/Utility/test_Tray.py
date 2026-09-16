from types import SimpleNamespace

import pytest

from Library.Utility.Tray import TrayAPI

class _SinkAPI:

    def __init__(self) -> None:
        self.levels = []

    def set_level(self, level) -> None:
        self.levels.append(level)

class _LogAPI:

    def __init__(self) -> None:
        self.console = _SinkAPI()
        self.file = _SinkAPI()
        self.errors = []

    def error(self, content) -> None:
        self.errors.append(content())

class _OwnedTrayAPI(TrayAPI):

    OWN = _LogAPI()

    def __init__(self) -> None:
        super().__init__(self.OWN)

@pytest.fixture
def ran(monkeypatch):
    import pystray
    trays = []
    monkeypatch.setattr(pystray, "Icon", lambda *args, **kwargs: SimpleNamespace(run=lambda: None, stop=lambda: None, update_menu=lambda: None))
    monkeypatch.setattr(TrayAPI, "run", lambda self: trays.append(self))
    return trays

def test_main_builds_the_base_tray_and_binds_the_callers_log(ran):
    log = _LogAPI()
    TrayAPI.main(log, lambda: pytest.fail("Headless"))
    assert ran[0]._log_ is log
    assert log.console.levels and log.file.levels

def test_main_keeps_the_log_a_subclass_bound_itself(ran):
    _OwnedTrayAPI.main(_LogAPI(), lambda: pytest.fail("Headless"))
    assert ran[0]._log_ is _OwnedTrayAPI.OWN

def test_main_runs_headless_when_the_tray_cannot_start(monkeypatch):
    import pystray
    def _unavailable_(*args, **kwargs): raise RuntimeError("No Display")
    monkeypatch.setattr(pystray, "Icon", _unavailable_)
    log, headless = _LogAPI(), []
    TrayAPI.main(log, lambda: headless.append(True))
    assert headless == [True]
    assert "No Display" in log.errors[0]