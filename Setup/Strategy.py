import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from Library.Logging import HandlerLoggingAPI
from Library.Strategy.Strategy import StrategyType

def generate_csharp_enum():
    content = """namespace cAlgo.Robots
{
    public enum StrategyType
    {
"""
    for strategy in StrategyType:
        content += f"        {strategy.name} = {strategy.value},\n"
    content += """    }
}
"""
    output_path = Path(__file__).parent.parent / "Sources" / "Robots" / "Connector" / "Connector" / "StrategyEnum.cs"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    return output_path

if __name__ == "__main__":
    with HandlerLoggingAPI() as logger:
        path = generate_csharp_enum()
        logger.info(f"Generated {path}")