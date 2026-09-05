from dataclasses import dataclass

from Library.Protocol.Update.Update import UpdateAPI
from Library.Protocol.Action.Action import ActionID

@dataclass(slots=True)
class DeniedUpdateAPI(UpdateAPI):

    ActionID: ActionID
    Reason: str

@dataclass(slots=True)
class ExceptionUpdateAPI(UpdateAPI):

    Reason: str

__all__ = [
    "DeniedUpdateAPI",
    "ExceptionUpdateAPI"
]