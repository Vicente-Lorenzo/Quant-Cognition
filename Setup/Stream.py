import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from Library.Protocol.Action.Action import Stream
from Setup.Enum import enum_block

def stream_block() -> str:
    return enum_block("Stream", [(s.name, s.value) for s in Stream], flags=True)