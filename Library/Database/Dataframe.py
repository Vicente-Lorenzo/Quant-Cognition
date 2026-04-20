from typing import Any

import numpy as np
np.set_printoptions(threshold=1000, linewidth=1000)
import pandas as pd
pd.options.display.max_rows = None
pd.options.display.max_columns = None
pd.options.display.width = 0
pd.options.display.max_colwidth = None
import polars as pl
pl.Config.set_tbl_cols(-1)
pl.Config.set_tbl_rows(-1)
pl.Config.set_tbl_width_chars(1000)
pl.Config.set_fmt_str_lengths(1000)
pl.Config.set_fmt_table_cell_list_len(-1)

from Library.Utility.Typing import MISSING, Missing
from Library.Database.Dataclass import DataclassAPI

class DataframeAPI:

    def __init__(self, *, legacy: bool = False, **kwargs) -> None:
        super().__init__(**kwargs)
        self._legacy_: bool = legacy

    @staticmethod
    def flatten(data: Any) -> list:
        if isinstance(data, pd.DataFrame):
            return data.to_dict(orient="records")  # type: ignore
        if isinstance(data, pd.Series):
            return data.to_list()  # type: ignore
        if isinstance(data, pl.DataFrame):
            return data.to_dicts()  # type: ignore
        if isinstance(data, pl.Series):
            return data.to_list()  # type: ignore
        if isinstance(data, DataclassAPI):
            return [data.dict()]
        if not isinstance(data, (tuple, list, set)):
            return [data] if data else []
        if all(isinstance(item, (list, tuple, set)) for item in data):
            return list(data)
        flat = []
        for item in data:
            flat.extend(DataframeAPI.flatten(item))
        return flat

    @staticmethod
    def parse(data: Any) -> tuple[list[str] | None, list[Any], bool]:
        if isinstance(data, pl.DataFrame):
            if data.is_empty(): return [], [], True  # type: ignore
            return list(data.columns), data.to_dicts(), True  # type: ignore
        if isinstance(data, pd.DataFrame):
            if data.empty: return [], [], True  # type: ignore
            return list(data.columns), data.to_dict(orient="records"), True  # type: ignore
        if isinstance(data, DataclassAPI):
            data_dict = data.dict()
            return list(data_dict.keys()), [data_dict], False
        if isinstance(data, dict):
            return list(data.keys()), [data], False
        if isinstance(data, (list, tuple)):
            if not data: return [], [], True
            if isinstance(data[0], dict):
                return list(data[0].keys()), list(data), True
            if isinstance(data[0], DataclassAPI):
                dicts = [d.dict() for d in data]
                return list(dicts[0].keys()), dicts, True
            if isinstance(data[0], (list, tuple)):
                return None, list(data), True
            return None, [data], False
        return None, [[data]], False

    def frame(self, data: Any, schema: dict = None, legacy: bool | Missing = MISSING) -> Any:
        data = self.flatten(data)
        df = pl.DataFrame(data=data, schema=schema, orient="row", strict=False)
        if len(df) > 0: df = df.select([s.shrink_dtype() for s in df.get_columns()])
        legacy = legacy if legacy is not MISSING else self._legacy_
        return df.to_pandas() if legacy else df