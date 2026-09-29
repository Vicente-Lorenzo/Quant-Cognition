from datetime import datetime

from Library.Database.Dataframe import DataframeAPI, pl

def test_a_column_empty_in_its_first_hundred_rows_keeps_its_later_values():
    rows = [{"UID": index, "Expiration": None} for index in range(150)] + [{"UID": 150, "Expiration": datetime(2026, 9, 27, 21, 52, 48, 638000)}]
    frame = DataframeAPI().frame(rows, legacy=False)
    assert frame.schema["Expiration"] == pl.Datetime("us") and frame["Expiration"][-1] == datetime(2026, 9, 27, 21, 52, 48, 638000)