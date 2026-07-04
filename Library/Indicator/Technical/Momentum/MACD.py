from __future__ import annotations

from typing import TYPE_CHECKING, Union

from Library.Database.Dataframe import pl
from Library.Indicator.Indicator import IndicatorMode
from Library.Indicator.Technical.Technical import TechnicalAPI, TechnicalType
from Library.Market.Series import SeriesAPI

if TYPE_CHECKING:
    from Library.Market.Market import MarketAPI

class MovingAverageConvergenceDivergenceAPI(TechnicalAPI):

    Type = TechnicalType.Momentum

    def __init__(self, name: str, slow_period: int, fast_period: int, signal_period: int, mode: IndicatorMode) -> None:
        super().__init__(name=name, window=slow_period + signal_period - 1, mode=mode)
        self.SlowPeriod: int = slow_period
        self.FastPeriod: int = fast_period
        self.SignalPeriod: int = signal_period
        self.MACD: SeriesAPI = SeriesAPI(f"{self.Name}.MACD")
        self.Signal: SeriesAPI = SeriesAPI(f"{self.Name}.Signal")
        self.Histogram: SeriesAPI = SeriesAPI(f"{self.Name}.Histogram")

    def _pad_(self) -> pl.DataFrame:
        return pl.DataFrame({
            f"{self.Name}.FastEMA": pl.Series([None], dtype=pl.Float64),
            f"{self.Name}.SlowEMA": pl.Series([None], dtype=pl.Float64),
            f"{self.Name}.MACD": pl.Series([None], dtype=pl.Float64),
            f"{self.Name}.Signal": pl.Series([None], dtype=pl.Float64),
            f"{self.Name}.Histogram": pl.Series([None], dtype=pl.Float64)
        })

    def batch(self, data: Union[pl.Series, pl.DataFrame]) -> pl.DataFrame:
        if data.is_empty(): return self._pad_()
        fast_ema = data.ewm_mean(span=self.FastPeriod, adjust=False)
        slow_ema = data.ewm_mean(span=self.SlowPeriod, adjust=False)
        macd = fast_ema - slow_ema
        nulls = [None] * (self.SlowPeriod - 1)
        if len(macd) > self.SlowPeriod - 1:
            macd = pl.Series(nulls + macd.to_list()[self.SlowPeriod - 1:])
        else:
            macd = pl.Series([None] * len(macd), dtype=pl.Float64)
        signal = macd.ewm_mean(span=self.SignalPeriod, adjust=False, ignore_nulls=True)
        if len(signal) > self.Window - 1:
            signal = pl.Series([None] * (self.Window - 1) + signal.to_list()[self.Window - 1:])
        else:
            signal = pl.Series([None] * len(signal), dtype=pl.Float64)
        histogram = macd - signal
        return pl.DataFrame({
            f"{self.Name}.FastEMA": fast_ema,
            f"{self.Name}.SlowEMA": slow_ema,
            f"{self.Name}.MACD": macd,
            f"{self.Name}.Signal": signal,
            f"{self.Name}.Histogram": histogram
        })

    def stream(self, data: Union[pl.Series, pl.DataFrame]) -> pl.DataFrame:
        prev_row = self._data_.row(-1, named=True) if self._data_ is not None and len(self._data_) > 0 else {}
        prev_fast = prev_row.get(f"{self.Name}.FastEMA")
        prev_slow = prev_row.get(f"{self.Name}.SlowEMA")
        prev_signal = prev_row.get(f"{self.Name}.Signal")
        new_price = (data[-1] if len(data) > 0 else None)
        if new_price is None: return self._pad_()
        alpha_fast = 2 / (self.FastPeriod + 1)
        alpha_slow = 2 / (self.SlowPeriod + 1)
        alpha_signal = 2 / (self.SignalPeriod + 1)
        if prev_fast is None:
            if len(data) < self.SlowPeriod: return self._pad_()
            new_fast = float(data.ewm_mean(span=self.FastPeriod, adjust=False)[-1])
            new_slow = float(data.ewm_mean(span=self.SlowPeriod, adjust=False)[-1])
            new_macd = new_fast - new_slow
            new_signal = None
            new_hist = None
        else:
            pf = float(prev_fast)
            ps = float(prev_slow)
            new_fast = (new_price - pf) * alpha_fast + pf
            new_slow = (new_price - ps) * alpha_slow + ps
            new_macd = new_fast - new_slow
            if prev_signal is None:
                macds = self.MACD.tail(dataframe=True).drop_nulls()
                if len(macds) >= self.SignalPeriod - 1:
                    seed = pl.Series(macds.to_list() + [new_macd]).ewm_mean(span=self.SignalPeriod, adjust=False)
                    new_signal = float(seed[-1])
                    new_hist = new_macd - new_signal
                else:
                    new_signal = None
                    new_hist = None
            else:
                psig = float(prev_signal)
                new_signal = (new_macd - psig) * alpha_signal + psig
                new_hist = new_macd - new_signal
        return pl.DataFrame({
            f"{self.Name}.FastEMA": pl.Series([new_fast], dtype=pl.Float64),
            f"{self.Name}.SlowEMA": pl.Series([new_slow], dtype=pl.Float64),
            f"{self.Name}.MACD": pl.Series([new_macd], dtype=pl.Float64),
            f"{self.Name}.Signal": pl.Series([new_signal], dtype=pl.Float64),
            f"{self.Name}.Histogram": pl.Series([new_hist], dtype=pl.Float64)
        })

    def init_data(self, market: MarketAPI) -> None:
        self._data_ = self.calculate(self._extract_(market), batch=True)
        self.MACD.init_data(self._data_)
        self.Signal.init_data(self._data_)
        self.Histogram.init_data(self._data_)

    def update_data(self, market: MarketAPI) -> None:
        if self._data_ is None: return self.init_data(market)
        df = self.calculate(self._extract_(market), batch=False)
        self._data_.extend(df)
        self.MACD.init_data(self._data_)
        self.Signal.init_data(self._data_)
        self.Histogram.init_data(self._data_)

    def update_offset(self, offset: int = 1) -> None:
        self.MACD.update_offset(offset)
        self.Signal.update_offset(offset)
        self.Histogram.update_offset(offset)

    def filter_buy(self, market: MarketAPI) -> bool:
        return bool(self.MACD.over(self.Signal))

    def filter_sell(self, market: MarketAPI) -> bool:
        return bool(self.MACD.under(self.Signal))

    def signal_buy(self, market: MarketAPI) -> bool:
        return bool(self.MACD.crossover(self.Signal))

    def signal_sell(self, market: MarketAPI) -> bool:
        return bool(self.MACD.crossunder(self.Signal))