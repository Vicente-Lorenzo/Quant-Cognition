import sys
import json
import filecmp
import subprocess

import pytest

from Library.Utility.Path import traceback_root
from Library.Utility.Runtime import split_arguments

ROOT = traceback_root()
GOLDENS = sorted([*(ROOT / "Tests" / "Golden" / "Offline").glob("Golden *"), *(ROOT / "Tests" / "Golden" / "Consistency").iterdir()])
EXPORTS = ("trades", "positions", "orders", "deals")

def _command_(golden) -> list:
    command = json.loads((golden / "Run.json").read_text(encoding="utf-8"))["Command"]
    arguments = split_arguments(command.split(" --run ", 1)[0])
    if "--parameters" not in arguments: arguments += ["--parameters", (golden / "Parameters.yml").relative_to(ROOT).as_posix()]
    if "--contract" not in arguments: arguments += ["--contract", (golden / "Contract.yml").relative_to(ROOT).as_posix()]
    return arguments

def test_every_golden_folder_is_complete():
    assert GOLDENS
    for golden in GOLDENS:
        assert all((golden / name).is_file() for name in ("Run.json", "Parameters.yml", "Contract.yml", *(f"{export}.csv" for export in EXPORTS))), golden

@pytest.mark.parametrize("golden", GOLDENS, ids=lambda golden: f"{golden.parent.name}/{golden.name}")
def test_a_golden_replays_byte_identically(golden, tmp_path):
    process = subprocess.run([sys.executable, "-m", "Library.System.Main", *_command_(golden), "--run", str(tmp_path)], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert process.returncode == 0, process.stderr[-2000:]
    for export in EXPORTS:
        produced = tmp_path / "Output" / "Export" / f"{export}.csv"
        assert produced.is_file() and filecmp.cmp(produced, golden / f"{export}.csv", shallow=False), f"{golden.name} {export}.csv drifted"