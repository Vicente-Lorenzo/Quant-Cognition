import sys
from argparse import ArgumentParser, Namespace
from typing import Union

from Library.Utility.Typing import MISSING, Missing

class CommandAPI:

    def __init__(self, *, name: str, refusals: tuple[type[Exception], ...] = (ValueError, PermissionError, LookupError)) -> None:
        self._name_ = name
        self._refusals_ = refusals

    @staticmethod
    def detail(row: Union[dict, None]) -> None:
        if row is None:
            print("(not found)")
            return
        for key, value in row.items():
            if value is not None: print(f"{key}: {value}")

    @staticmethod
    def table(rows: list[dict], columns: Union[list, Missing] = MISSING) -> None:
        if not rows:
            print("(none)")
            return
        columns = list(rows[0]) if columns is MISSING else columns
        cells = [{column: "" if row.get(column) is None else str(row.get(column)) for column in columns} for row in rows]
        widths = {column: max(len(column), *(len(cell[column]) for cell in cells)) for column in columns}
        print("  ".join(column.ljust(widths[column]) for column in columns))
        for cell in cells: print("  ".join(cell[column].ljust(widths[column]) for column in columns))

    def arguments(self, parser: ArgumentParser) -> None:
        return None

    def parse(self, argv: Union[list, None] = None) -> Namespace:
        parser = ArgumentParser(prog=self._name_)
        self.arguments(parser)
        return parser.parse_args(argv)

    def run(self, args: Namespace) -> int:
        raise NotImplementedError

    def main(self, argv: Union[list, None] = None) -> int:
        for stream in (sys.stdout, sys.stderr):
            if hasattr(stream, "reconfigure"): stream.reconfigure(encoding="utf-8", errors="replace")
        args = self.parse(argv)
        try: return self.run(args) or 0
        except self._refusals_ as error:
            print(f"Rejected · {error}")
            return 1