import pytest

from Library.Logging import VerboseLevel

def test_members_and_values():
    assert [(level.name, level.value) for level in VerboseLevel] == [
        ("Silent", 0), ("Exception", 1), ("Error", 2), ("Warning", 3),
        ("Alert", 4), ("Info", 5), ("Debug", 6)]

def test_ordering_is_verbosity_ascending():
    assert VerboseLevel.Silent.value < VerboseLevel.Exception.value < VerboseLevel.Error.value
    assert VerboseLevel.Error.value < VerboseLevel.Warning.value < VerboseLevel.Alert.value
    assert VerboseLevel.Alert.value < VerboseLevel.Info.value < VerboseLevel.Debug.value

def test_standard_mapping_is_severity_descending():
    assert VerboseLevel.Debug.Standard == 10
    assert VerboseLevel.Info.Standard == 20
    assert VerboseLevel.Alert.Standard == 25
    assert VerboseLevel.Warning.Standard == 30
    assert VerboseLevel.Error.Standard == 40
    assert VerboseLevel.Exception.Standard == 50
    assert VerboseLevel.Silent.Standard == 60

def test_standard_is_inverse_of_verbosity():
    levels = [level for level in VerboseLevel]
    assert [level.Standard for level in sorted(levels, key=lambda item: item.value)] == sorted(
        [level.Standard for level in levels], reverse=True)

@pytest.mark.parametrize("value,expected", [
    (0, VerboseLevel.Debug), (10, VerboseLevel.Debug), (15, VerboseLevel.Debug),
    (20, VerboseLevel.Info), (24, VerboseLevel.Info), (25, VerboseLevel.Alert),
    (29, VerboseLevel.Alert), (30, VerboseLevel.Warning), (39, VerboseLevel.Warning),
    (40, VerboseLevel.Error), (49, VerboseLevel.Error), (50, VerboseLevel.Exception),
    (59, VerboseLevel.Exception), (60, VerboseLevel.Silent), (999, VerboseLevel.Silent)])
def test_standard_resolution_ladder(value, expected):
    assert VerboseLevel.standard(value) is expected

def test_resolve_accepts_enum():
    assert VerboseLevel.resolve(VerboseLevel.Info) is VerboseLevel.Info

def test_resolve_accepts_name():
    assert VerboseLevel.resolve("Warning") is VerboseLevel.Warning

def test_resolve_accepts_standard_integer():
    assert VerboseLevel.resolve(30) is VerboseLevel.Warning

def test_resolve_rejects_unknown_name():
    with pytest.raises(KeyError):
        VerboseLevel.resolve("Verbose")

def test_resolve_rejects_bool():
    with pytest.raises(TypeError):
        VerboseLevel.resolve(True)

def test_resolve_rejects_unsupported_type():
    with pytest.raises(TypeError):
        VerboseLevel.resolve(3.5)

def test_parity_with_generated_csharp_enum(connector_enums):
    assert list(connector_enums["VerboseLevel"].items()) == [(level.name, level.value) for level in VerboseLevel]