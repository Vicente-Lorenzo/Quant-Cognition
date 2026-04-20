import threading
from datetime import datetime, timezone

from Library.Database.Dataframe import pd, pl
from Library.Utility.Service import ServiceAPI
from Library.Utility.Typing import MISSING, Missing

_TIMEFRAME_MAP_ = {
    "M1": 1, "M2": 2, "M3": 3, "M4": 4, "M5": 5, "M10": 6, "M15": 7, "M30": 8,
    "H1": 9, "H4": 10, "H12": 11, "D1": 12, "W1": 13, "MN1": 14
}
_TIMEFRAME_REVERSE_ = {v: k for k, v in _TIMEFRAME_MAP_.items()}
_QUOTE_MAP_ = {"BID": 1, "ASK": 2}
_PRICE_SCALE_ = 100000.0

def _timeframe_id_(value: str | int) -> int:
    if isinstance(value, int): return value
    return _TIMEFRAME_MAP_[str(value).upper()]

def _timeframe_uid_(value: int | str) -> str:
    if isinstance(value, str): return value.upper()
    return _TIMEFRAME_REVERSE_.get(int(value), str(value))

def _quote_(value: str | int) -> int:
    if isinstance(value, int): return value
    return _QUOTE_MAP_[str(value).upper()]

def _millis_(value: datetime) -> int:
    if value.tzinfo is None: value = value.replace(tzinfo=timezone.utc)
    return int(value.timestamp() * 1000)

class MarketAPI(ServiceAPI):

    def ticks(self,
              symbol: int,
              start: datetime,
              stop: datetime = None,
              quote: str | int = "BID",
              legacy: bool | Missing = MISSING) -> pd.DataFrame | pl.DataFrame:
        from ctrader_open_api import Protobuf
        stop = stop or datetime.now(timezone.utc)
        quote_id = _quote_(quote)
        price_col = "BidPrice" if quote_id == 1 else "AskPrice"
        def _fetch_():
            from_ts = _millis_(start)
            to_ts = _millis_(stop)
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
                    data.append({
                        "SecurityUID": int(symbol),
                        "DateTime": datetime.fromtimestamp(cumulative_ts / 1000, tz=timezone.utc),
                        price_col: cumulative_price / _PRICE_SCALE_
                    })
                if not bool(getattr(response, "hasMore", False)): break
                earliest = min(r["DateTime"] for r in data[batch_start:])
                new_to = int(earliest.timestamp() * 1000) - 1
                if new_to <= from_ts: break
                to_ts = new_to
            data.sort(key=lambda r: r["DateTime"])
            return self._api_.frame(data, legacy=legacy)
        timer, df = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Ticks Operation: Fetched {len(df)} ticks ({timer.result()})")
        return df

    def bars(self,
             symbol: int,
             start: datetime,
             stop: datetime = None,
             timeframe: str | int = "M1",
             count: int | None = None,
             legacy: bool | Missing = MISSING) -> pd.DataFrame | pl.DataFrame:
        from ctrader_open_api import Protobuf
        stop = stop or datetime.now(timezone.utc)
        tf_id = _timeframe_id_(timeframe)
        tf_uid = _timeframe_uid_(tf_id)
        def _fetch_():
            kwargs = {
                "ctidTraderAccountId": self._api_._account_id_,
                "symbolId": int(symbol),
                "period": tf_id,
                "fromTimestamp": _millis_(start),
                "toTimestamp": _millis_(stop)
            }
            if count is not None: kwargs["count"] = int(count)
            request = Protobuf.get("ProtoOAGetTrendbarsReq", **kwargs)
            response = self._api_._send_(request)
            data = []
            for bar in response.trendbar:
                low = bar.low
                ts = datetime.fromtimestamp(bar.utcTimestampInMinutes * 60, tz=timezone.utc)
                data.append({
                    "SecurityUID": int(symbol),
                    "TimeframeUID": tf_uid,
                    "DateTime": ts,
                    "OpenBidPrice": (low + bar.deltaOpen) / _PRICE_SCALE_,
                    "HighBidPrice": (low + bar.deltaHigh) / _PRICE_SCALE_,
                    "LowBidPrice": low / _PRICE_SCALE_,
                    "CloseBidPrice": (low + bar.deltaClose) / _PRICE_SCALE_,
                    "TickVolume": bar.volume
                })
            return self._api_.frame(data, legacy=legacy)
        timer, df = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Bars Operation: Fetched {len(df)} bars ({timer.result()})")
        return df

    def depth(self,
              symbol: int,
              timeout: float = 5.0,
              legacy: bool | Missing = MISSING) -> pd.DataFrame | pl.DataFrame:
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
                        "BidPrice": (q.bid / _PRICE_SCALE_) if q.HasField("bid") else None,
                        "AskPrice": (q.ask / _PRICE_SCALE_) if q.HasField("ask") else None
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
            return self._api_.frame(rows, legacy=legacy)
        timer, df = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Depth Operation: Fetched {len(df)} depth quotes ({timer.result()})")
        return df
