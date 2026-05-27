from Library.Portfolio.Position import PositionType

def position_block() -> str:
    from Setup.Enum import enum_block
    members = [(member.name, member.value) for member in PositionType]
    return enum_block("PositionTypeID", members)