from pathlib import Path

OUTPUT_PATH = Path(__file__).parent.parent / "Sources" / "Robots" / "Connector" / "Connector" / "Enum.cs"

def enum_block(name: str, members) -> str:
    body = "\n".join(f"        {member} = {value}," for member, value in members)
    return f"    public enum {name}\n    {{\n{body}\n    }}"

def write_enum_file(blocks: list[str]) -> Path:
    body = "\n\n".join(blocks)
    content = f"namespace cAlgo.Robots\n{{\n{body}\n}}"
    OUTPUT_PATH.write_text(content, encoding="utf-8", newline="\n")
    return OUTPUT_PATH

def write_all() -> Path:
    from Setup.Strategy import strategy_block
    from Setup.Logging import logging_block
    from Setup.System import system_block
    from Setup.Update import update_block
    from Setup.Action import action_block
    return write_enum_file([strategy_block(), logging_block(), system_block(), update_block(), action_block()])