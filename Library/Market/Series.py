from __future__ import annotations

from typing import Union, TYPE_CHECKING

from Library.Database.Dataframe import pl
from Library.Market.Price import PriceMode
from Library.Utility.Typing import MISSING

if TYPE_CHECKING:
    from Library.Market.Point import PointAPI
    from Library.Market.Tick import TickAPI

class SeriesAPI:

    def __init__(self, prefix: str = "", multiple: bool = False, parent: Union[SeriesAPI, None] = None, mode: PriceMode = PriceMode.Bid, point: bool = False) -> None:
        self._prefix_: str = prefix
        self._multiple_: bool = multiple or point
        self._point_: bool = point
        self._parent_: Union[SeriesAPI, None] = parent
        self._mode_ = mode
        self._offset_: int = 1
        self._data_: Union[pl.DataFrame, None] = None
        self._columns_: Union[list[str], None] = None
        p = f"{prefix}." if prefix else ""
        if point:
            self.AskTick = SeriesAPI(f"{p}AskTick", True, self, mode)
            self.MidTick = SeriesAPI(f"{p}MidTick", True, self, mode)
            self.BidTick = SeriesAPI(f"{p}BidTick", True, self, mode)
            self.Ask = self.AskTick.Ask
            self.Mid = self.MidTick.Mid
            self.Bid = self.BidTick.Bid
            self._children_ = [self.AskTick, self.MidTick, self.BidTick]
            self._leaves_ = [self.Ask, self.Bid]
        elif multiple:
            self.Ask = SeriesAPI(f"{p}Ask", False, self, mode)
            self.Mid = MidSeriesAPI(f"{p}Mid", self, mode)
            self.Bid = SeriesAPI(f"{p}Bid", False, self, mode)
            self.AskBaseConversion = SeriesAPI(f"{p}AskBaseConversion", False, self, mode)
            self.BidBaseConversion = SeriesAPI(f"{p}BidBaseConversion", False, self, mode)
            self.AskQuoteConversion = SeriesAPI(f"{p}AskQuoteConversion", False, self, mode)
            self.BidQuoteConversion = SeriesAPI(f"{p}BidQuoteConversion", False, self, mode)
            self.Volume = SeriesAPI(f"{p}Volume", False, self, mode)
            self._children_ = [self.Ask, self.Bid, self.AskBaseConversion, self.BidBaseConversion, self.AskQuoteConversion, self.BidQuoteConversion, self.Volume]
            self._leaves_ = self._children_
        else:
            self._children_ = []
            self._leaves_ = []

    @property
    def Price(self) -> SeriesAPI:
        if not self._multiple_: return self
        return self.Ask if self._mode_ == PriceMode.Ask else self.Mid if self._mode_ == PriceMode.Mid else self.Bid

    def init_data(self, data: pl.DataFrame) -> None:
        self._data_ = data
        for child in self._children_: child.init_data(data)

    def update_offset(self, offset: int = 1) -> None:
        self._offset_ = offset
        for child in self._children_: child.update_offset(offset)

    def _column_(self) -> list[str]:
        if self._columns_ is None:
            if not self._multiple_:
                self._columns_ = [self._prefix_]
            else:
                cols = []
                for c in self._children_: cols.extend(c._column_())
                self._columns_ = cols
        return self._columns_

    def dataframe(self) -> Union[pl.DataFrame, pl.Series]:
        if self._data_ is None: return pl.DataFrame() if self._multiple_ else pl.Series(self._prefix_, dtype=pl.Float64)
        if self._multiple_:
            columns = set(self._data_.columns)
            return self._data_.select([c for c in self._column_() if c in columns])
        try: return self._data_.get_column(self._prefix_)
        except pl.exceptions.ColumnNotFoundError: return pl.Series(self._prefix_, dtype=pl.Float64)

    def _slice_(self, shift: int, length: int) -> pl.DataFrame:
        if self._data_ is None or self._data_.is_empty(): return pl.DataFrame()
        start = max(0, self._data_.height - self._offset_ - shift - length + 1)
        end = self._data_.height - self._offset_ - shift + 1
        return pl.DataFrame() if start >= end or end <= 0 else self._data_.slice(start, end - start)

    @staticmethod
    def _tick_(row: dict, prefix: str) -> TickAPI:
        from Library.Market.Tick import TickAPI
        p = f"{prefix}." if prefix else ""
        return TickAPI(UID=row.get(f"{p}UID", row.get("UID")), Timestamp=row.get(f"{p}Timestamp", row.get("Timestamp")), Security=row.get(f"{p}Security", row.get("Security")), Ask=row.get(f"{p}Ask", row.get("Ask")), Bid=row.get(f"{p}Bid", row.get("Bid")), AskBaseConversion=row.get(f"{p}AskBaseConversion", row.get("AskBaseConversion")), BidBaseConversion=row.get(f"{p}BidBaseConversion", row.get("BidBaseConversion")), AskQuoteConversion=row.get(f"{p}AskQuoteConversion", row.get("AskQuoteConversion")), BidQuoteConversion=row.get(f"{p}BidQuoteConversion", row.get("BidQuoteConversion")), Volume=row.get(f"{p}Volume", row.get("Volume")))

    def _item_(self, row: dict) -> Union[TickAPI, PointAPI]:
        if not self._point_: return self._tick_(row, self._prefix_)
        from Library.Market.Point import PointAPI
        return PointAPI(AskTick=self._tick_(row, self.AskTick._prefix_), MidTick=self._tick_(row, self.MidTick._prefix_), BidTick=self._tick_(row, self.BidTick._prefix_))

    def _each_(self, other: Union[SeriesAPI, float, int], method, shift: int, dataframe: bool) -> Union[list[bool], pl.DataFrame]:
        if not isinstance(other, SeriesAPI) or not other._multiple_: raise ValueError("Ambiguous comparison.")
        r = {c._prefix_: method(c, o, shift) for c, o in zip(self._leaves_, other._leaves_)}
        return pl.DataFrame(r) if dataframe else list(r.values())

    def last(self, shift: int = 0, dataframe: bool = False):
        if not self._multiple_:
            s = self.dataframe()
            if isinstance(s, pl.DataFrame) or s.is_empty() or self._offset_ + shift > s.len() or self._offset_ + shift <= 0: return None
            return s[-(self._offset_ + shift)]
        df = self._slice_(shift, 1)
        if dataframe: return df
        if df.is_empty(): return None
        return self._item_(df.to_dicts()[0])

    def tail(self, n: int = MISSING, dataframe: bool = False):
        if not self._multiple_:
            s = self.dataframe()
            if isinstance(s, pl.DataFrame) or s.is_empty(): return pl.Series(self._prefix_, dtype=pl.Float64)
            end = s.len() - self._offset_ + 1
            return pl.Series(self._prefix_, dtype=pl.Float64) if end <= 0 else s[(0 if n is MISSING else max(0, end - n)):end]
        df = self._slice_(0, n if n is not MISSING else (self._data_.height if self._data_ is not None else 0))
        if dataframe: return df
        if df.is_empty(): return []
        return [self._item_(r) for r in df.to_dicts()]

    def over(self, other: Union[SeriesAPI, float, int], shift: int = 0, dataframe: bool = False) -> Union[bool, list[bool], pl.DataFrame]:
        if self._multiple_: return self._each_(other, SeriesAPI.over, shift, dataframe)
        lst = self.last(shift)
        if isinstance(other, SeriesAPI):
            if other._multiple_: raise ValueError("Ambiguous comparison.")
            olst = other.last(shift)
            return lst > olst if lst is not None and olst is not None else False
        return lst > other if lst is not None and other is not None else False

    def under(self, other: Union[SeriesAPI, float, int], shift: int = 0, dataframe: bool = False) -> Union[bool, list[bool], pl.DataFrame]:
        if self._multiple_: return self._each_(other, SeriesAPI.under, shift, dataframe)
        lst = self.last(shift)
        if isinstance(other, SeriesAPI):
            if other._multiple_: raise ValueError("Ambiguous comparison.")
            olst = other.last(shift)
            return lst < olst if lst is not None and olst is not None else False
        return lst < other if lst is not None and other is not None else False

    def crossover(self, other: Union[SeriesAPI, float, int], shift: int = 0, dataframe: bool = False) -> Union[bool, list[bool], pl.DataFrame]:
        if self._multiple_: return self._each_(other, SeriesAPI.crossover, shift, dataframe)
        return self.over(other, shift) and self.under(other, shift + 1)

    def crossunder(self, other: Union[SeriesAPI, float, int], shift: int = 0, dataframe: bool = False) -> Union[bool, list[bool], pl.DataFrame]:
        if self._multiple_: return self._each_(other, SeriesAPI.crossunder, shift, dataframe)
        return self.under(other, shift) and self.over(other, shift + 1)

    def __repr__(self) -> str:
        return repr(self.dataframe())

class MidSeriesAPI(SeriesAPI):

    def __init__(self, prefix: str, parent: SeriesAPI, mode: PriceMode) -> None:
        super().__init__(prefix, False, parent, mode)

    def dataframe(self) -> pl.Series:
        return ((self._parent_.Ask.dataframe() + self._parent_.Bid.dataframe()) / 2).alias(self._prefix_)

    def last(self, shift: int = 0, dataframe: bool = False) -> Union[float, None]:
        ask, bid = self._parent_.Ask.last(shift), self._parent_.Bid.last(shift)
        return None if ask is None or bid is None else (ask + bid) / 2

    def tail(self, n: int = MISSING, dataframe: bool = False) -> pl.Series:
        return ((self._parent_.Ask.tail(n) + self._parent_.Bid.tail(n)) / 2).alias(self._prefix_)