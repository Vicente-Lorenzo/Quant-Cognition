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