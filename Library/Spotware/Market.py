from typing import Union
import threading
from datetime import datetime, timezone

from Library.Database.Dataframe import pd, pl
from Library.Utility.Service import ServiceAPI
from Library.Utility.Typing import MISSING, Missing
from Library.Utility.Datetime import datetime_to_timestamp, timestamp_to_datetime
from Library.Market.Tick import TickAPI
from Library.Market.Bar import BarAPI

class MarketAPI(ServiceAPI):

    _TIMEFRAME_MAP_ = {
        "M1": 1, "M2": 2, "M3": 3, "M4": 4, "M5": 5, "M10": 6, "M15": 7, "M30": 8,
        "H1": 9, "H4": 10, "H12": 11, "D1": 12, "W1": 13, "MN1": 14
    }
    _TIMEFRAME_REVERSE_ = {v: k for k, v in _TIMEFRAME_MAP_.items()}
    _QUOTE_MAP_ = {"BID": 1, "ASK": 2}
    _PRICE_SCALE_ = 100000.0

    @classmethod
    def _timeframe_id_(cls, value: Union[str, int]) -> int:
        if isinstance(value, int): return value
        return cls._TIMEFRAME_MAP_[str(value).upper()]

    @classmethod
    def _timeframe_uid_(cls, value: Union[int, str]) -> str:
        if isinstance(value, str): return value.upper()
        return cls._TIMEFRAME_REVERSE_.get(int(value), str(value))

    @classmethod
    def _quote_(cls, value: Union[str, int]) -> int:
        if isinstance(value, int): return value
        return cls._QUOTE_MAP_[str(value).upper()]

    @classmethod
    def _millis_(cls, value: datetime) -> int:
        if value.tzinfo is None: value = value.replace(tzinfo=timezone.utc)
        return int(datetime_to_timestamp(value, milliseconds=True))

    def ticks(self,
              symbol: int,
              start: datetime,
              stop: datetime = None,
              quote: Union[str, int] = "BID",
              legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame, list[TickAPI]]:
        from ctrader_open_api import Protobuf
        stop = stop or datetime.now(timezone.utc)
        quote_id = self._quote_(quote)
        def _fetch_():
            from_ts = self._millis_(start)
            to_ts = self._millis_(stop)
            data = []
            while True:
                request = Protobuf.get("ProtoOAGetTickDataReq",
                                       ctidTraderAccountId=self._api_._account_id_,
                                       symbolId=int(symbol),
                                       type=quote_id,
                                       fromTimestamp=from_ts,
                                       toTimestamp=to_ts)
                response = self._api_._send_(request)
                ticks = list(response.tickData)
                if not ticks: break
                cumulative_ts = 0
                cumulative_price = 0
                batch_start = len(data)
                for i, t in enumerate(ticks):
                    cumulative_ts = t.timestamp if i == 0 else cumulative_ts + t.timestamp
                    cumulative_price = t.tick if i == 0 else cumulative_price + t.tick
                    dt = timestamp_to_datetime(cumulative_ts, milliseconds=True)
                    price = cumulative_price / self._PRICE_SCALE_
                    tick = TickAPI(
                        SecurityUID=int(symbol),
                        DateTime=dt.replace(tzinfo=timezone.utc),
                        AskPrice=price if quote_id == 2 else None,
                        BidPrice=price if quote_id == 1 else None,
                        db=self._api_._db_ if hasattr(self._api_, "_db_") else None
                    )
                    data.append(tick)
                if not getattr(response, "hasMore", False): break
                earliest = min(r.DateTime for r in data[batch_start:])
                new_to = int(datetime_to_timestamp(earliest, milliseconds=True)) - 1
                if new_to <= from_ts: break
                to_ts = new_to
            data.sort(key=lambda r: r.DateTime)
            if legacy is MISSING: return data
            return self._api_.frame(data, legacy=legacy)
        timer, result = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Ticks Operation: Fetched {len(result)} ticks ({timer.result()})")
        return result

    def bars(self,
             symbol: int,
             start: datetime,
             stop: datetime = None,
             timeframe: Union[str, int] = "M1",
             count: Union[int, None] = None,
             legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame, list[BarAPI]]:
        from ctrader_open_api import Protobuf
        stop = stop or datetime.now(timezone.utc)
        tf_id = self._timeframe_id_(timeframe)
        tf_uid = self._timeframe_uid_(tf_id)
        def _fetch_():
            kwargs = {
                "ctidTraderAccountId": self._api_._account_id_,
                "symbolId": int(symbol),
                "period": tf_id,
                "fromTimestamp": self._millis_(start),
                "toTimestamp": self._millis_(stop)
            }
            if count is not None: kwargs["count"] = int(count)
            request = Protobuf.get("ProtoOAGetTrendbarsReq", **kwargs)
            response = self._api_._send_(request)
            data = []
            for bar in response.trendbar:
                low = bar.low
                ts = timestamp_to_datetime(bar.utcTimestampInMinutes * 60, milliseconds=False)
                b = BarAPI(
                    SecurityUID=int(symbol),
                    TimeframeUID=tf_uid,
                    DateTime=ts.replace(tzinfo=timezone.utc),
                    OpenBidPrice=(low + bar.deltaOpen) / self._PRICE_SCALE_,
                    HighBidPrice=(low + bar.deltaHigh) / self._PRICE_SCALE_,
                    LowBidPrice=low / self._PRICE_SCALE_,
                    CloseBidPrice=(low + bar.deltaClose) / self._PRICE_SCALE_,
                    TickVolume=bar.volume,
                    db=self._api_._db_ if hasattr(self._api_, "_db_") else None
                )
                data.append(b)
            if legacy is MISSING: return data
            return self._api_.frame(data, legacy=legacy)
        timer, result = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Bars Operation: Fetched {len(result)} bars ({timer.result()})")
        return result

    def depth(self,
              symbol: int,
              timeout: float = 5.0,
              legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame, list[dict]]:
        from ctrader_open_api import Protobuf
        sid = int(symbol)
        def _fetch_():
            book: dict[int, dict] = {}
            done = threading.Event()
            def handler(message):
                if done.is_set(): return
                payload = Protobuf.extract(message)
                if type(payload).__name__ != "ProtoOADepthEvent": return
                if int(payload.symbolId) != sid: return
                for q in payload.newQuotes:
                    book[int(q.id)] = {
                        "SecurityUID": sid,
                        "QuoteId": int(q.id),
                        "Size": int(q.size),
                        "BidPrice": (q.bid / self._PRICE_SCALE_) if q.HasField("bid") else None,
                        "AskPrice": (q.ask / self._PRICE_SCALE_) if q.HasField("ask") else None
                    }
                for qid in payload.deletedQuotes:
                    book.pop(int(qid), None)
                if book: done.set()
            self._api_._subscribe_(handler)
            try:
                sub = Protobuf.get("ProtoOASubscribeDepthQuotesReq",
                                   ctidTraderAccountId=self._api_._account_id_,
                                   symbolId=[sid])
                self._api_._send_(sub)
                done.wait(timeout=timeout)
            finally:
                self._api_._unsubscribe_(handler)
                try:
                    unsub = Protobuf.get("ProtoOAUnsubscribeDepthQuotesReq",
                                         ctidTraderAccountId=self._api_._account_id_,
                                         symbolId=[sid])
                    self._api_._send_(unsub)
                except Exception: pass
            rows = sorted(book.values(), key=lambda r: (r["BidPrice"] is None, -(r["BidPrice"] or 0), r["AskPrice"] or 0))
            if legacy is MISSING: return rows
            return self._api_.frame(rows, legacy=legacy)
        timer, result = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Depth Operation: Fetched {len(result)} depth quotes ({timer.result()})")
        return result