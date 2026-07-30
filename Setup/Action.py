import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from Library.Logging import LoggingAPI
from Library.Protocol.Action.Action import ActionID
from Setup.Enum import enum_block, write_all

def action_block() -> str:
    return enum_block("ActionID", [(a.name, a.value) for a in ActionID])

if __name__ == "__main__":
    with LoggingAPI() as logger:
        path = write_all()
        logger.info(lambda: f"Generated {path}")