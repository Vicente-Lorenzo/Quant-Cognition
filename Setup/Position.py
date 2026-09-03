from Library.Portfolio.Position import PositionType
from Setup.Enum import enum_block

def position_block() -> str:
    return enum_block("PositionTypeID", PositionType)