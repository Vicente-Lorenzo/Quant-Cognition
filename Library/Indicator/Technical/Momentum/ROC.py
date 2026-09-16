import math
from typing import Union

from Library.Database.Dataframe import pl
from Library.Indicator.Technical.Technical import NeutralSignalAPI, TechnicalAPI, TechnicalType

class RateOfChangeAPI(NeutralSignalAPI):

    Type = TechnicalType.Momentum
    Parameters = (TechnicalAPI.PERIOD.revised(default=12), TechnicalAPI.MODE)

    def batch(self, data: Union[pl.Series, pl.DataFrame]) -> pl.DataFrame:
        if data.is_empty(): return self._pad_()
        roc = (data / data.shift(self.Window)).log()
        return pl.DataFrame({self.Name: roc})

    def stream(self, data: Union[pl.Series, pl.DataFrame]) -> pl.DataFrame:
        new_close = (data[-1] if len(data) > 0 else None)
        old_close = (data[-(self.Window + 1)] if len(data) > self.Window else None)
        if new_close is None or old_close is None or new_close <= 0 or old_close <= 0: return self._pad_()
        return self._scalar_(math.log(new_close / old_close))