from typing import Union
from Library.Database.Dataframe import pl

class SeriesAPI:

    def __init__(self, sid: str):
        self._sid: str = sid
        self._offset: int = 1
        self._data: Union[pl.DataFrame, None] = None

    def data(self) -> pl.Series:
        return self._data[self._sid] if self._data is not None else pl.Series()

    def head(self, n: Union[int, None] = None) -> pl.Series:
        return self.data().head(n)

    def tail(self, n: Union[int, None] = None) -> pl.Series:
        return self.data().tail(n)

    def init_data(self, data: pl.DataFrame) -> None:
        self._data = data

    def update_offset(self, offset: int) -> None:
        self._offset = offset

    def last(self, shift: int = 0) -> Union[float, int]:
        return self.data()[-(self._offset + shift)]

    def over(self, other, shift: int = 0) -> bool:
        this_last = self.last(shift)
        if isinstance(other, SeriesAPI):
            other_last = other.last(shift)
            return this_last > other_last if this_last is not None and other_last is not None else False
        return this_last > other if this_last is not None and other is not None else False

    def under(self, other, shift: int = 0) -> bool:
        this_last = self.last(shift)
        if isinstance(other, SeriesAPI):
            other_last = other.last(shift)
            return this_last < other_last if this_last is not None and other_last is not None else False
        return this_last < other if this_last is not None and other is not None else False

    def crossover(self, other, shift: int = 0) -> bool:
        return self.over(other, shift) and self.under(other, shift + 1)

    def crossunder(self, other, shift: int = 0) -> bool:
        return self.under(other, shift) and self.over(other, shift + 1)

    def __repr__(self) -> str:
        return repr(self.data())
