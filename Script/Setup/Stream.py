from Library.Protocol.Action.Action import Stream
from Script.Setup.Enum import enum_block

def stream_block() -> str:
    return enum_block("Stream", Stream, flags=True)