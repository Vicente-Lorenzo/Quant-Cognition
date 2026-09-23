import pytest

from Library.Utility.Command import CommandAPI

class _Probe_(CommandAPI):

    def __init__(self, failure: Exception, **kwargs) -> None:
        super().__init__(name="Probe", **kwargs)
        self._failure_ = failure

    def arguments(self, parser) -> None:
        parser.add_argument("--value", type=int, default=0)

    def run(self, args) -> int:
        if self._failure_ is not None: raise self._failure_
        return args.value

def test_a_command_returns_its_exit_code(capsys):
    assert _Probe_(None).main(["--value", "3"]) == 3
    assert _Probe_(None).main([]) == 0

def test_a_refusal_prints_and_exits_one(capsys):
    assert _Probe_(PermissionError("Denied")).main([]) == 1
    assert capsys.readouterr().out.strip() == "Rejected · Denied"

def test_without_refusals_every_error_propagates():
    with pytest.raises(ValueError, match="Broken"):
        _Probe_(ValueError("Broken"), refusals=()).main([])

def test_a_table_aligns_columns_and_blanks_nothing(capsys):
    CommandAPI.table([{"Name": "a", "Value": None}, {"Name": "longer", "Value": 2}])
    assert capsys.readouterr().out.splitlines() == ["Name    Value", "a            ", "longer  2    "]
    CommandAPI.table([])
    assert capsys.readouterr().out.strip() == "(none)"

def test_a_detail_skips_missing_values(capsys):
    CommandAPI.detail({"Name": "a", "Value": None})
    assert capsys.readouterr().out.strip() == "Name: a"
    CommandAPI.detail(None)
    assert capsys.readouterr().out.strip() == "(not found)"