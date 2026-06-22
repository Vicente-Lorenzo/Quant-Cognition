from pathlib import Path

OUTPUT_PATH = Path(__file__).parent.parent / "Sources" / "Robots" / "Connector" / "Connector" / "Enum.cs"

def enum_block(name: str, members, flags: bool = False) -> str:
    body = "\n".join(f"        {member} = {value}," for member, value in members)
    attribute = "    [System.Flags]\n" if flags else ""
    return f"{attribute}    public enum {name}\n    {{\n{body}\n    }}"

def write_enum_file(blocks: list[str]) -> Path:
    body = "\n\n".join(blocks)
    content = f"namespace Connector\n{{\n{body}\n}}"
    OUTPUT_PATH.write_text(content, encoding="utf-8", newline="\n")
    return OUTPUT_PATH

def write_all() -> Path:
    from Setup.Position import position_block
    from Setup.Strategy import strategy_block
    from Setup.Logging import logging_block
    from Setup.System import system_block
    from Setup.Update import update_block
    from Setup.Action import action_block
    from Setup.Stream import stream_block
    return write_enum_file([position_block(), strategy_block(), logging_block(), system_block(), update_block(), action_block(), stream_block()])