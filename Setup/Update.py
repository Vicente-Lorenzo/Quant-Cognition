from Library.Protocol.Update.Update import UpdateID
from Setup.Enum import enum_block

def update_block() -> str:
    return enum_block("UpdateID", UpdateID)