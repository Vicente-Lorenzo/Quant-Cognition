import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from Library.Logging import HandlerLoggingAPI
from Library.Logging.Logging import VerboseLevel
from Setup.Enum import enum_block, write_enum_file

def logging_block() -> str:
    return enum_block("VerboseLevel", [(v.name, v.value) for v in VerboseLevel])

if __name__ == "__main__":
    from Setup.Strategy import strategy_block
    with HandlerLoggingAPI() as logger:
        path = write_enum_file([strategy_block(), logging_block()])
        logger.info(f"Generated {path}")