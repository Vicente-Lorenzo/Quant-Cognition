import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from Library.Logging import LoggingAPI
from Library.Protocol.Update.Update import UpdateID
from Setup.Enum import enum_block, write_all

def update_block() -> str:
    return enum_block("UpdateID", [(u.name, u.value) for u in UpdateID])

if __name__ == "__main__":
    with LoggingAPI() as logger:
        path = write_all()
        logger.info(lambda: f"Generated {path}")