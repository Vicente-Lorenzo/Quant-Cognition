import json

from Library.Database.Dataframe import pl
from Library.System.System import SystemAPI

def test_stringify_encodes_list_columns_as_json():
    df = pl.DataFrame({"UID": [[2, 3], [5]]}, schema={"UID": pl.List(pl.Int64)})
    encoded = SystemAPI._stringify_(df)
    assert encoded.schema["UID"] == pl.String
    assert encoded["UID"].to_list() == ["[2, 3]", "[5]"]
    assert [json.loads(value) for value in encoded["UID"]] == [[2, 3], [5]]

def test_stringify_never_emits_a_series_repr():
    df = pl.DataFrame({"UID": [[2, 3]]}, schema={"UID": pl.List(pl.Int64)})
    assert "Series" not in SystemAPI._stringify_(df)["UID"][0]

def test_stringify_encodes_struct_columns_as_json():
    df = pl.DataFrame({"Detail": [{"Position": 1, "Direction": "Sell"}]})
    encoded = SystemAPI._stringify_(df)
    assert json.loads(encoded["Detail"][0]) == {"Position": 1, "Direction": "Sell"}

def test_stringify_leaves_flat_frames_untouched():
    df = pl.DataFrame({"UID": [1, 2], "Volume": [1000.0, 2000.0]})
    assert SystemAPI._stringify_(df).schema == df.schema

def test_stringify_survives_a_csv_round_trip(tmp_path):
    df = pl.DataFrame({"UID": [[2, 3], [5]], "Position": [1, 2]}, schema={"UID": pl.List(pl.Int64), "Position": pl.Int64})
    path = tmp_path / "deals.csv"
    SystemAPI._stringify_(df).write_csv(str(path))
    restored = pl.read_csv(str(path))
    assert [json.loads(value) for value in restored["UID"]] == [[2, 3], [5]]