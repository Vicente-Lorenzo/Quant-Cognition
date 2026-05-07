from __future__ import annotations

from typing import Union, TYPE_CHECKING
from Library.Database.Dataframe import pl

if TYPE_CHECKING:
    from Library.Market.Tick import TickAPI

class SeriesAPI:

    def __init__(self, prefix: str = "", multiple: bool = False, parent: Union[SeriesAPI, None] = None) -> None:
        self._prefix_: str = prefix
        self._multiple_: bool = multiple
        self._parent_: Union[SeriesAPI, None] = parent
        self._offset_: int = 1
        self._data_: Union[pl.DataFrame, None] = None
        if self._multiple_:
            p = f"{prefix}." if prefix else ""
            self.Ask = SeriesAPI(f"{p}Ask", False, self)
            self.Bid = SeriesAPI(f"{p}Bid", False, self)
            self.AskBaseConversion = SeriesAPI(f"{p}AskBaseConversion", False, self)
            self.BidBaseConversion = SeriesAPI(f"{p}BidBaseConversion", False, self)
            self.AskQuoteConversion = SeriesAPI(f"{p}AskQuoteConversion", False, self)
            self.BidQuoteConversion = SeriesAPI(f"{p}BidQuoteConversion", False, self)
            self.Volume = SeriesAPI(f"{p}Volume", False, self)
            self._children_ = [self.Ask, self.Bid, self.AskBaseConversion, self.BidBaseConversion, self.AskQuoteConversion, self.BidQuoteConversion, self.Volume]
        else: self._children_ = []

    def init_data(self, data: pl.DataFrame) -> None:
        self._data_ = data
        for child in self._children_: child.init_data(data)

    def update_offset(self, offset: int = 1) -> None:
        self._offset_ = offset
        for child in self._children_: child.update_offset(offset)

    def _column_(self) -> list[str]:
        if not self._multiple_: return [self._prefix_]
        cols = []
        for c in self._children_: cols.extend(c._column_())
        return cols

    def dataframe(self) -> Union[pl.DataFrame, pl.Series]:
        if self._data_ is None: return pl.DataFrame() if self._multiple_ else pl.Series(self._prefix_, dtype=pl.Float64)
        if self._multiple_: return self._data_.select([c for c in self._column_() if c in self._data_.columns])
        return self._data_[self._prefix_] if self._prefix_ in self._data_.columns else pl.Series(self._prefix_, dtype=pl.Float64)

    def _slice_(self, shift: int, length: int) -> pl.DataFrame:
        if self._data_ is None or self._data_.is_empty(): return pl.DataFrame()
        start = max(0, self._data_.height - self._offset_ - shift - length + 1)
        end = self._data_.height - self._offset_ - shift + 1
        return pl.DataFrame() if start >= end or end <= 0 else self._data_.slice(start, end - start)

    def last(self, shift: int = 0, dataframe: bool = False):
        if not self._multiple_:
            s = self.dataframe()
            if isinstance(s, pl.DataFrame) or s.is_empty() or self._offset_ + shift > s.len() or self._offset_ + shift <= 0: return None
            return s[-(self._offset_ + shift)]
        df = self._slice_(shift, 1)
        if dataframe: return df
        if df.is_empty(): return None
        r = df.to_dicts()[0]
        p = f"{self._prefix_}." if self._prefix_ else ""
        from Library.Market.Tick import TickAPI
        return TickAPI(UID=r.get(f"{p}UID", r.get("UID")), Timestamp=r.get(f"{p}Timestamp", r.get("Timestamp")), Security=r.get(f"{p}Security", r.get("Security")), Ask=r.get(f"{p}Ask", r.get("Ask")), Bid=r.get(f"{p}Bid", r.get("Bid")), AskBaseConversion=r.get(f"{p}AskBaseConversion", r.get("AskBaseConversion")), BidBaseConversion=r.get(f"{p}BidBaseConversion", r.get("BidBaseConversion")), AskQuoteConversion=r.get(f"{p}AskQuoteConversion", r.get("AskQuoteConversion")), BidQuoteConversion=r.get(f"{p}BidQuoteConversion", r.get("BidQuoteConversion")), Volume=r.get(f"{p}Volume", r.get("Volume")))

    def tail(self, n: Union[int, None] = None, dataframe: bool = False):
        if not self._multiple_:
            s = self.dataframe()
            if isinstance(s, pl.DataFrame) or s.is_empty(): return pl.Series(self._prefix_, dtype=pl.Float64)
            end = s.len() - self._offset_ + 1
            return pl.Series(self._prefix_, dtype=pl.Float64) if end <= 0 else s[(0 if n is None else max(0, end - n)):end]
        df = self._slice_(0, n if n is not None else (self._data_.height if self._data_ is not None else 0))
        if dataframe: return df
        if df.is_empty(): return []
        p = f"{self._prefix_}." if self._prefix_ else ""
        from Library.Market.Tick import TickAPI
        return [TickAPI(UID=r.get(f"{p}UID", r.get("UID")), Timestamp=r.get(f"{p}Timestamp", r.get("Timestamp")), Security=r.get(f"{p}Security", r.get("Security")), Ask=r.get(f"{p}Ask", r.get("Ask")), Bid=r.get(f"{p}Bid", r.get("Bid")), AskBaseConversion=r.get(f"{p}AskBaseConversion", r.get("AskBaseConversion")), BidBaseConversion=r.get(f"{p}BidBaseConversion", r.get("BidBaseConversion")), AskQuoteConversion=r.get(f"{p}AskQuoteConversion", r.get("AskQuoteConversion")), BidQuoteConversion=r.get(f"{p}BidQuoteConversion", r.get("BidQuoteConversion")), Volume=r.get(f"{p}Volume", r.get("Volume"))) for r in df.to_dicts()]

    def over(self, other: Union[SeriesAPI, float, int], shift: int = 0, dataframe: bool = False) -> Union[bool, list[bool], pl.DataFrame]:
        if self._multiple_:
            if not isinstance(other, SeriesAPI) or not other._multiple_: raise ValueError("Ambiguous comparison.")
            r = {c._prefix_: c.over(o, shift) for c, o in zip(self._children_, other._children_)}
            return pl.DataFrame(r) if dataframe else list(r.values())
        lst = self.last(shift)
        if isinstance(other, SeriesAPI):
            if other._multiple_: raise ValueError("Ambiguous comparison.")
            olst = other.last(shift)
            return lst > olst if lst is not None and olst is not None else False
        return lst > other if lst is not None and other is not None else False

    def under(self, other: Union[SeriesAPI, float, int], shift: int = 0, dataframe: bool = False) -> Union[bool, list[bool], pl.DataFrame]:
        if self._multiple_:
            if not isinstance(other, SeriesAPI) or not other._multiple_: raise ValueError("Ambiguous comparison.")
            r = {c._prefix_: c.under(o, shift) for c, o in zip(self._children_, other._children_)}
            return pl.DataFrame(r) if dataframe else list(r.values())
        lst = self.last(shift)
        if isinstance(other, SeriesAPI):
            if other._multiple_: raise ValueError("Ambiguous comparison.")
            olst = other.last(shift)
            return lst < olst if lst is not None and olst is not None else False
        return lst < other if lst is not None and other is not None else False

    def crossover(self, other: Union[SeriesAPI, float, int], shift: int = 0, dataframe: bool = False) -> Union[bool, list[bool], pl.DataFrame]:
        if self._multiple_:
            if not isinstance(other, SeriesAPI) or not other._multiple_: raise ValueError("Ambiguous comparison.")
            r = {c._prefix_: c.crossover(o, shift) for c, o in zip(self._children_, other._children_)}
            return pl.DataFrame(r) if dataframe else list(r.values())
        return self.over(other, shift) and self.under(other, shift + 1)

    def crossunder(self, other: Union[SeriesAPI, float, int], shift: int = 0, dataframe: bool = False) -> Union[bool, list[bool], pl.DataFrame]:
        if self._multiple_:
            if not isinstance(other, SeriesAPI) or not other._multiple_: raise ValueError("Ambiguous comparison.")
            r = {c._prefix_: c.crossunder(o, shift) for c, o in zip(self._children_, other._children_)}
            return pl.DataFrame(r) if dataframe else list(r.values())
        return self.under(other, shift) and self.over(other, shift + 1)

    def __repr__(self) -> str:
        return repr(self.dataframe())