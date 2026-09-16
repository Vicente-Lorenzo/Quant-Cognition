from Library.Strategy.Strategy import StrategyType
from Script.Setup.Enum import enum_block

def strategy_block() -> str:
    return enum_block("StrategyType", StrategyType)