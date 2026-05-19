from enum import IntEnum

from Library.Engine import MachineAPI, EngineAPI, StateAPI, TransitionAPI
from Library.Protocol.Update import UpdateID, CompleteUpdateAPI
from Library.Protocol.Action import CompleteActionAPI
from Library.System.Lifecycle import LifecycleAPI

def _complete_update_():
    return CompleteUpdateAPI(Account=None, Security=None, Market=None, Technical=None, Fundamental=None, Sentimental=None, Portfolio=None)

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

def test_state_end_flag_only_set_on_creation():
    machine = MachineAPI(Name="Test", Events=len(UpdateID))
    s1 = machine.state(name="Start", end=False)
    s2 = machine.state(name="Start", end=True)
    assert s1 is s2
    assert s1.End is False

def test_machine_first_state_becomes_initial():
    machine = MachineAPI(Name="Test", Events=len(UpdateID))
    s1 = machine.state(name="A")
    machine.state(name="B")
    assert machine.At is s1

def test_machine_transition_changes_state():
    machine = MachineAPI(Name="Test", Events=len(UpdateID))
    s1 = machine.state(name="S1")
    s2 = machine.state(name="S2", end=True)
    s1.on(event=UpdateID.Complete, to=s2, action=None, reason="Done")
    machine.perform(UpdateID.Complete, _complete_update_())
    assert machine.At is s2

def test_machine_transition_runs_action_and_returns_actions():
    machine = MachineAPI(Name="Test", Events=len(UpdateID))
    s1 = machine.state(name="S1")
    s2 = machine.state(name="S2", end=True)
    def my_action(update):
        return [CompleteActionAPI()]
    s1.on(event=UpdateID.Complete, to=s2, action=my_action, reason="Done")
    actions = machine.perform(UpdateID.Complete, _complete_update_())
    assert len(actions) == 1
    assert isinstance(actions[0], CompleteActionAPI)

def test_machine_perform_no_transition_returns_empty():
    machine = MachineAPI(Name="Test", Events=len(UpdateID))
    machine.state(name="Start")
    actions = machine.perform(UpdateID.Complete, _complete_update_())
    assert actions == []

def test_machine_action_returning_none_yields_empty_list():
    machine = MachineAPI(Name="Test", Events=len(UpdateID))
    s1 = machine.state(name="S1")
    s2 = machine.state(name="S2", end=True)
    s1.on(event=UpdateID.Complete, to=s2, action=lambda u: None, reason=None)
    actions = machine.perform(UpdateID.Complete, _complete_update_())
    assert actions == []
    assert machine.At is s2

def test_transition_perform_returns_action_result():
    s = StateAPI(Name="X", End=True, events=len(UpdateID))
    t = TransitionAPI(To=s, Action=lambda u: [CompleteActionAPI()], Reason="x")
    result = t.perform(None)
    assert len(result) == 1

def test_transition_perform_with_no_action_returns_none():
    s = StateAPI(Name="X", End=True, events=len(UpdateID))
    t = TransitionAPI(To=s, Action=None, Reason=None)
    assert t.perform(None) is None

def test_engine_is_terminated_when_all_machines_at_end():
    m1 = MachineAPI(Name="A", Events=len(UpdateID))
    m1.state(name="End", end=True)
    m2 = MachineAPI(Name="B", Events=len(UpdateID))
    m2.state(name="End", end=True)
    engine = EngineAPI(machines=[m1, m2])
    assert engine.IsTerminated is True

def test_engine_is_not_terminated_when_any_machine_not_at_end():
    m1 = MachineAPI(Name="A", Events=len(UpdateID))
    m1.state(name="End", end=True)
    m2 = MachineAPI(Name="B", Events=len(UpdateID))
    m2.state(name="Running")
    engine = EngineAPI(machines=[m1, m2])
    assert engine.IsTerminated is False

def test_engine_perform_returns_first_non_empty_actions():
    m1 = MachineAPI(Name="A", Events=len(UpdateID))
    a1 = m1.state(name="A1")
    a2 = m1.state(name="A2")
    a1.on(event=UpdateID.Complete, to=a2, action=None, reason=None)
    m2 = MachineAPI(Name="B", Events=len(UpdateID))
    b1 = m2.state(name="B1")
    b2 = m2.state(name="B2")
    b1.on(event=UpdateID.Complete, to=b2, action=lambda u: [CompleteActionAPI()], reason=None)
    engine = EngineAPI(machines=[m1, m2])
    actions = engine.perform(UpdateID.Complete, _complete_update_())
    assert len(actions) == 1

def test_engine_perform_transitions_all_machines():
    m1 = MachineAPI(Name="A", Events=len(UpdateID))
    a1 = m1.state(name="A1")
    a2 = m1.state(name="A2")
    a1.on(event=UpdateID.Complete, to=a2, action=None, reason=None)
    m2 = MachineAPI(Name="B", Events=len(UpdateID))
    b1 = m2.state(name="B1")
    b2 = m2.state(name="B2")
    b1.on(event=UpdateID.Complete, to=b2, action=lambda u: [CompleteActionAPI()], reason=None)
    engine = EngineAPI(machines=[m1, m2])
    engine.perform(UpdateID.Complete, _complete_update_())
    assert m1.At is a2
    assert m2.At is b2

def test_engine_portable_with_custom_enum():
    class TestEvent(IntEnum):
        Start = 0
        Stop = 1
    machine = MachineAPI(Name="Custom", Events=len(TestEvent))
    s1 = machine.state(name="Active")
    s2 = machine.state(name="Done", end=True)
    s1.on(event=TestEvent.Stop, to=s2, action=None, reason="Stopped")
    machine.perform(TestEvent.Stop, None)
    assert machine.At is s2

def test_engine_accepts_raw_int_events():
    machine = MachineAPI(Name="RawInt", Events=10)
    s1 = machine.state(name="A")
    s2 = machine.state(name="B", end=True)
    s1.on(event=5, to=s2, action=None, reason=None)
    machine.perform(5, None)
    assert machine.At is s2

def test_lifecycle_api_default_construction():
    engine = LifecycleAPI()
    assert engine.IsTerminated is False

def test_lifecycle_api_termination_via_shutdown():
    engine = LifecycleAPI()
    engine.perform(UpdateID.Shutdown, _complete_update_())
    assert engine.IsTerminated is True

def test_lifecycle_api_with_custom_machines():
    sys_m = MachineAPI(Name="Sys", Events=len(UpdateID))
    sys_m.state(name="End", end=True)
    strat_m = MachineAPI(Name="Strat", Events=len(UpdateID))
    strat_m.state(name="End", end=True)
    sig_m = MachineAPI(Name="Sig", Events=len(UpdateID))
    sig_m.state(name="End", end=True)
    risk_m = MachineAPI(Name="Risk", Events=len(UpdateID))
    risk_m.state(name="End", end=True)
    engine = LifecycleAPI(system_machine=sys_m, strategy_machine=strat_m, signal_machine=sig_m, risk_machine=risk_m)
    assert engine.IsTerminated is True
