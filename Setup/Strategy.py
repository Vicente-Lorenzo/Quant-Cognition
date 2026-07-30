import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from Library.Logging import LoggingAPI
from Library.Strategy.Strategy import StrategyType
from Setup.Enum import enum_block, write_all

def strategy_block() -> str:
    return enum_block("StrategyType", [(s.name, s.value) for s in StrategyType])

if __name__ == "__main__":
    with LoggingAPI() as logger:
        path = write_all()
        logger.info(lambda: f"Generated {path}")