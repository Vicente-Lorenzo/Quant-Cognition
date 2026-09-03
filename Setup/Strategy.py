from Library.Strategy.Strategy import StrategyType
from Setup.Enum import enum_block

def strategy_block() -> str:
    return enum_block("StrategyType", StrategyType)