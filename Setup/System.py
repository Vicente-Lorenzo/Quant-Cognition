import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from Library.Logging import HandlerLoggingAPI
from Library.System.System import SystemType
from Setup.Enum import enum_block, write_all

def system_block() -> str:
    return enum_block("SystemMode", [(s.name, s.value) for s in SystemType])

if __name__ == "__main__":
    with HandlerLoggingAPI() as logger:
        path = write_all()
        logger.info(f"Generated {path}")