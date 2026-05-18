from __future__ import annotations

from typing import Union

from Library.Engine import EngineAPI, MachineAPI
from Library.Protocol.Update import UpdateID

class LifecycleAPI(EngineAPI):

    __slots__ = ()

    def __init__(self,
                 system_machine: Union[MachineAPI, None] = None,
                 strategy_machine: Union[MachineAPI, None] = None,
                 signal_machine: Union[MachineAPI, None] = None,
                 risk_machine: Union[MachineAPI, None] = None) -> None:
        super().__init__(machines=[
            system_machine or self._dummy_(),
            strategy_machine or self._dummy_(),
            signal_machine or self._dummy_(),
            risk_machine or self._dummy_()
        ])

    @staticmethod
    def _dummy_() -> MachineAPI:
        machine = MachineAPI(Name="Dummy Management", Events=len(UpdateID))
        execution = machine.state(name="Execution")
        termination = machine.state(name="Termination", end=True)
        execution.on(event=UpdateID.Shutdown, to=termination, action=None, reason="Safely Terminated")
        return machine

__all__ = ["LifecycleAPI"]