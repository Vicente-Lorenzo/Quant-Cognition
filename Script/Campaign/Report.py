import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from Library.Database.Dataframe import pl
from Script.Campaign.Campaign import root

def _percent_(value) -> str:
    return "" if value is None else f"{100.0 * value:+.1f}"

def _number_(value, digits: int = 2) -> str:
    return "" if value is None else f"{value:.{digits}f}"

def table(frame: pl.DataFrame) -> str:
    folds = [column for column in frame.columns if column.startswith("F") and column[1:].isdigit()]
    header = ["Pair", "Model", "Gates", "Pass A · B", *[f"V{2017 + int(column[1:])}" for column in folds], "V Total", "V Pair", "V DD", "V Sharpe", "V Sortino", "V Calmar", "V Sterling",
              "T 2025", "T Pair", "T DD", "T Sharpe", "T Sortino", "T Calmar", "T Sterling", "Full", "Full Pair", "Full DD", "Full Sharpe", "Full Sortino", "Full Calmar", "Full Sterling",
              "α/yr", "β", "Long", "Weaker", "Hold d", "Flips", "Regime", "Null", "p"]
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    for row in frame.iter_rows(named=True):
        cells = [row["Pair"], f"{row['Arm']}·{row['Seed']}", f"{row['Gates']}/5 {row['Status'][:4]}", row["Passing"], *[_percent_(row[column]) for column in folds],
                 _percent_(row["VReturn"]), _percent_(row["VPair"]), _percent_(row["VMaxDD"]), _number_(row["VSharpe"]), _number_(row["VSortino"]), _number_(row["VCalmar"]), _number_(row["VSterling"]),
                 _percent_(row["TReturn"]), _percent_(row["TPair"]), _percent_(row["TMaxDD"]), _number_(row["TSharpe"]), _number_(row["TSortino"]), _number_(row["TCalmar"]), _number_(row["TSterling"]),
                 _percent_(row["AReturn"]), _percent_(row["APair"]), _percent_(row["AMaxDD"]), _number_(row["ASharpe"]), _number_(row["ASortino"]), _number_(row["ACalmar"]), _number_(row["ASterling"]),
                 _percent_(row["Alpha"]), _number_(row["Beta"]), _percent_(row["Long"]), _percent_(row["Weaker"]), _number_(row["MeanHoldDays"], 1), str(row["Flips"]), _number_(row["Regime"], 1), _number_(row["NullMedian"], 1), _number_(row["P"], 3)]
        lines.append("| " + " | ".join(str(cell) for cell in cells) + " |")
    return "\n".join(lines)

def main() -> int:
    summary = root() / "Summary.csv"
    if not summary.is_file():
        print("No evaluated pair yet")
        return 0
    sys.stdout.reconfigure(encoding="utf-8")
    print(table(pl.read_csv(summary, infer_schema_length=None)))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())