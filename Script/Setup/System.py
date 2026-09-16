from Library.System.System import SystemType
from Script.Setup.Enum import enum_block

def system_block() -> str:
    return enum_block("SystemMode", SystemType)