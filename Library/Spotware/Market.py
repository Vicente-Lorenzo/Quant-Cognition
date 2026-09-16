from typing import Union
from datetime import datetime
from itertools import accumulate
from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOADepthEvent
from ctrader_open_api.messages.OpenApiModelMessages_pb2 import ProtoOAQuoteType, ProtoOATrendbarPeriod

from Library.Database.Dataframe import pd, pl
from Library.Market.Bar import BarAPI
from Library.Market.Tick import TickAPI
from Library.Universe.Timeframe import TimeframeAPI
from Library.Utility.Datetime import utc_now
from Library.Utility.Service import ServiceAPI
from Library.Utility.Typing import MISSING, Missing

class MarketAPI(ServiceAPI):

    _MINUTE_ = 60000

    def _period_(self, timeframe: Union[str, int]) -> int:
        return self._api_._code_(ProtoOATrendbarPeriod, TimeframeAPI.normalize(timeframe) if isinstance(timeframe, str) else timeframe)

    def _trendbar_(self, bar, symbol: int, timeframe: str) -> dict:
        price = self._api_._price_
        return {
            "Symbol": symbol,
            "Timeframe": timeframe,
            str(TickAPI.ID.Timestamp): self._api_._stamp_(bar.utcTimestampInMinutes * self._MINUTE_),
            "Open": price(bar.low + bar.deltaOpen),
            "High": price(bar.low + bar.deltaHigh),
            "Low": price(bar.low),
            "Close": price(bar.low + bar.deltaClose),
            str(BarAPI.ID.Volume): int(bar.volume)
        }

    def _quote_(self, symbol: int, quote) -> dict:
        return {
            "Symbol": symbol,
            "Quote": int(quote.id),
            "Size": self._api_._units_(quote.size),
            str(TickAPI.ID.Bid): self._api_._optional_(quote, "bid", self._api_._price_),
            str(TickAPI.ID.Ask): self._api_._optional_(quote, "ask", self._api_._price_)
        }

    def ticks(self,
              symbol: int,
              start: datetime,
              stop: Union[datetime, None] = None,
              quote: Union[str, int] = "Bid",
              legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame]:
        sid, side = int(symbol), self._api_._code_(ProtoOAQuoteType, quote)
        stamp = str(TickAPI.ID.Timestamp)
        column = str(TickAPI.ID.Ask) if side == ProtoOAQuoteType.Value("ASK") else str(TickAPI.ID.Bid)
        def _fetch_():
            lower, upper = self._api_._epoch_(start), self._api_._epoch_(stop or utc_now())
            stamps, prices = [], []
            while True:
                response = self._api_._request_("ProtoOAGetTickDataReq", symbolId=sid, type=side, fromTimestamp=lower, toTimestamp=upper)
                if not response.tickData: break
                batch = len(stamps)
                stamps.extend(accumulate(entry.timestamp for entry in response.tickData))
                prices.extend(accumulate(entry.tick for entry in response.tickData))
                if not response.hasMore: break
                earliest = min(stamps[batch:]) - 1
                if earliest <= lower: break
                upper = earliest
            frame = pl.DataFrame({stamp: stamps, column: prices}, schema={stamp: pl.Int64, column: pl.Int64})
            frame = frame.select(pl.lit(sid, dtype=pl.Int64).alias("Symbol"), pl.from_epoch(pl.col(stamp), time_unit="ms"), pl.col(column) / self._api_._PRICE_SCALE_).sort(stamp)
            return frame.to_pandas() if self._api_.legacy(legacy) else frame
        timer, result = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Ticks Operation: Fetched {len(result)} ticks ({timer.result()})")
        return result

    def bars(self,
             symbol: int,
             start: datetime,
             stop: Union[datetime, None] = None,
             timeframe: Union[str, int] = "M1",
             count: Union[int, None] = None,
             legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame]:
        period = self._period_(timeframe)
        label = ProtoOATrendbarPeriod.Name(period)
        def _fetch_():
            fields = {"symbolId": int(symbol), "period": period, "fromTimestamp": self._api_._epoch_(start), "toTimestamp": self._api_._epoch_(stop or utc_now())}
            if count is not None: fields["count"] = int(count)
            response = self._api_._request_("ProtoOAGetTrendbarsReq", **fields)
            return self._api_.frame([self._trendbar_(bar, int(symbol), label) for bar in response.trendbar], legacy=legacy)
        timer, result = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Bars Operation: Fetched {len(result)} bars ({timer.result()})")
        return result

    def depth(self,
              symbol: int,
              timeout: float = 5.0,
              legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame]:
        sid = int(symbol)
        bid, ask = str(TickAPI.ID.Bid), str(TickAPI.ID.Ask)
        def _fetch_():
            book: dict[int, dict] = {}
            def _decode_(payload) -> list:
                if not isinstance(payload, ProtoOADepthEvent) or payload.symbolId != sid: return []
                book.update({int(quote.id): self._quote_(sid, quote) for quote in payload.newQuotes})
                for quote in payload.deletedQuotes: book.pop(int(quote), None)
                return [book] if book else []
            subscribe = self._api_._message_("ProtoOASubscribeDepthQuotesReq", symbolId=[sid])
            unsubscribe = self._api_._message_("ProtoOAUnsubscribeDepthQuotesReq", symbolId=[sid])
            self._api_._listen_(subscribe, unsubscribe, _decode_, lambda update: None, limit=1, timeout=timeout)
            rows = sorted(book.values(), key=lambda row: (row[bid] is None, -(row[bid] or 0), row[ask] or 0))
            return self._api_.frame(rows, legacy=legacy)
        timer, result = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Depth Operation: Fetched {len(result)} depth quotes ({timer.result()})")
        return result