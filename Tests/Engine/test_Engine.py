from Library.Engine import MachineAPI, EngineAPI
from Library.Protocol.Update import UpdateID, CompleteUpdateAPI
from Library.Protocol.Action import CompleteActionAPI
from Library.System.Engine import SystemEngineAPI

def test_state_creation():
    machine = MachineAPI(Name="Test", Events=len(UpdateID))
    state = machine.state(name="Start")
    assert state.Name == "Start"
    assert state.End is False
    assert machine.At is state

def test_state_get_or_create():
    machine = MachineAPI(Name="Test", Events=len(UpdateID))
    s1 = machine.state(name="Start")
    s2 = machine.state(name="Start")
    assert s1 is s2

def test_machine_transition():
    machine = MachineAPI(Name="Test", Events=len(UpdateID))
    state1 = machine.state(name="S1")
    state2 = machine.state(name="S2", end=True)

    def my_action(update):
        return [CompleteActionAPI()]

    state1.on(event=UpdateID.Complete, to=state2, action=my_action, reason="Done")

    update = CompleteUpdateAPI(Account=None, Market=None, Technical=None, Fundamental=None, Sentimental=None, Portfolio=None)
    actions = machine.perform(UpdateID.Complete, update)

    assert machine.At is state2
    assert len(actions) == 1
    assert isinstance(actions[0], CompleteActionAPI)

def test_engine_generic():
    m1 = MachineAPI(Name="A", Events=len(UpdateID))
    m1.state(name="End", end=True)
    m2 = MachineAPI(Name="B", Events=len(UpdateID))
    m2.state(name="End", end=True)

    engine = EngineAPI(machines=[m1, m2])
    assert engine.IsTerminated is True

def test_system_engine_api():
    sys_m = MachineAPI(Name="Sys", Events=len(UpdateID))
    sys_m.state(name="End", end=True)
    strat_m = MachineAPI(Name="Strat", Events=len(UpdateID))
    strat_m.state(name="End2", end=True)
    sig_m = MachineAPI(Name="Sig", Events=len(UpdateID))
    sig_m.state(name="End3", end=True)
    risk_m = MachineAPI(Name="Risk", Events=len(UpdateID))
    risk_m.state(name="End4", end=True)

    engine = SystemEngineAPI(system_machine=sys_m, strategy_machine=strat_m, signal_machine=sig_m, risk_machine=risk_m)
    assert engine.IsTerminated is True

    engine2 = SystemEngineAPI()
    assert engine2.IsTerminated is False

    update = CompleteUpdateAPI(Account=None, Market=None, Technical=None, Fundamental=None, Sentimental=None, Portfolio=None)
    engine2.perform_update_shutdown(update)
    assert engine2.IsTerminated is True
