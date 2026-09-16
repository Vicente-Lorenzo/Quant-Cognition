from Library.Protocol.Action.Action import ActionID
from Script.Setup.Enum import enum_block

def action_block() -> str:
    return enum_block("ActionID", ActionID)