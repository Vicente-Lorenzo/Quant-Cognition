from pathlib import Path

from Script.Data.Service import DataServiceAPI, SupervisorAPI
from Library.Utility.Progress import Phase, ProgressAPI

class FlakyAPI(SupervisorAPI):

    def __init__(self) -> None:
        super().__init__(script=Path("unused.py"), flag="--key", name="Probe", database="Tests", vault="Tests", interval=0.01)
        self.calls = 0

    def _supervise_(self) -> None:
        self.calls += 1
        if self.calls == 1: raise ConnectionError("Database restarting")
        self.stop()

class ReadyAPI(DataServiceAPI):

    def work(self) -> None:
        self.ready("Caught Up")
        self.ready("Again")

class BrokenAPI(DataServiceAPI):

    def work(self) -> None:
        raise LookupError("Nothing to serve")

def phases(output: str) -> list:
    return [line.split(ProgressAPI.SENTINEL, 1)[1] for line in output.splitlines() if ProgressAPI.SENTINEL in line]

def test_a_supervisor_survives_a_failed_round_and_supervises_again():
    service = FlakyAPI()
    service.work()
    assert service.calls == 2

def test_a_service_reports_running_once_and_terminating_on_exit(capfd):
    assert ReadyAPI(database="Tests", vault="Tests").serve() == 0
    reported = phases(capfd.readouterr().out)
    assert reported == [f'{{"phase":"{Phase.Running.name}"}}', f'{{"phase":"{Phase.Terminating.name}"}}']

def test_a_failing_service_exits_one_and_still_reports_terminating(capfd):
    assert BrokenAPI(database="Tests", vault="Tests").serve() == 1
    assert phases(capfd.readouterr().out) == [f'{{"phase":"{Phase.Terminating.name}"}}']
class IdleAPI(SupervisorAPI):

    def __init__(self) -> None:
        super().__init__(script=Path("unused.py"), flag="--key", name="Idle", database="Tests", vault="Tests", interval=0.01)

    def tracked(self) -> dict:
        return {}

def test_a_supervisor_with_nothing_to_track_is_running_at_once(capfd):
    service = IdleAPI()
    service._supervise_()
    assert service._ready_ and phases(capfd.readouterr().out) == [f'{{"phase":"{Phase.Running.name}"}}']

def test_a_refused_token_is_rotated_once_however_many_workers_ask(monkeypatch):
    service = ReadyAPI(database="Tests", vault="Tests")
    stored, rotations = ["old"], []
    monkeypatch.setattr(service._vault_, "administrator", lambda: "admin")
    monkeypatch.setattr(service._vault_, "credentials", lambda service=None, by=None: [{"UID": "probe-renew", "Name": "cTrader ID"}])
    monkeypatch.setattr(service._vault_, "rotate", lambda uid: rotations.append(uid) or stored.append("new"))
    monkeypatch.setattr(service, "_values_", lambda: {"AccessToken": stored[-1]})
    service._token_ = "old"
    assert service._renew_() == "new" and rotations == ["probe-renew"]
    other = ReadyAPI(database="Tests", vault="Tests")
    for name, value in (("administrator", service._vault_.administrator), ("credentials", service._vault_.credentials), ("rotate", service._vault_.rotate)): monkeypatch.setattr(other._vault_, name, value)
    monkeypatch.setattr(other, "_values_", lambda: {"AccessToken": stored[-1]})
    other._token_ = "old"
    assert other._renew_() == "new" and rotations == ["probe-renew"]