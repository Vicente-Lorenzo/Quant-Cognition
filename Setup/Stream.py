from Library.Protocol.Action.Action import Stream
from Setup.Enum import enum_block

def stream_block() -> str:
    return enum_block("Stream", Stream, flags=True)