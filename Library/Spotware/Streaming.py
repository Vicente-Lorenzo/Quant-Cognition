import threading
from typing import Callable

from Library.Utility.Service import ServiceAPI
from Library.Spotware.Market import _PRICE_SCALE_, _timeframe_id_, _timeframe_uid_

_SPOT_EVENT_ = "ProtoOASpotEvent"
_DEPTH_EVENT_ = "ProtoOADepthEvent"

class StreamingAPI(ServiceAPI):

    def ticks(self,
              symbols: int | list[int],
              callback: Callable,
              frame: bool = True,
              limit: int | None = None,
              timeout: int | None = None) -> None:
        from ctrader_open_api import Protobuf
        ids = [int(i) for i in self._api_.flatten(symbols)]
        try:
            self.connect()
            counter = {"n": 0}
            done = threading.Event()
            def handler(message):
                if done.is_set(): return
                payload = Protobuf.extract(message)
                if type(payload).__name__ != _SPOT_EVENT_: return
                if int(payload.symbolId) not in ids: return
                data = {"SecurityUID": int(payload.symbolId)}
                if payload.HasField("bid"): data["BidPrice"] = payload.bid / _PRICE_SCALE_
                if payload.HasField("ask"): data["AskPrice"] = payload.ask / _PRICE_SCALE_
                if payload.HasField("timestamp"): data["Timestamp"] = int(payload.timestamp)
                if len(data) > 1:
                    callback(self._api_.frame([data]) if frame else data)
                    counter["n"] += 1
                    if limit is not None and counter["n"] >= limit: done.set()
            self._api_._subscribe_(handler)
            try:
                request = Protobuf.get("ProtoOASubscribeSpotsReq",
                                       ctidTraderAccountId=self._api_._account_id_,
                                       symbolId=ids)
                self._api_._send_(request)
                done.wait(timeout=timeout)
            finally:
                self._api_._unsubscribe_(handler)
                try:
                    unsub = Protobuf.get("ProtoOAUnsubscribeSpotsReq",
                                         ctidTraderAccountId=self._api_._account_id_,
                                         symbolId=ids)
                    self._api_._send_(unsub)
                except Exception: pass
        except KeyboardInterrupt:
            self._log_.info(lambda: "Ticks Stream: Interrupted by User")
        except Exception as e:
            self._log_.error(lambda: "Ticks Stream: Failed")
            self._log_.exception(lambda: str(e))
            raise

    def bars(self,
             symbol: int,
             timeframe: str | int,
             callback: Callable,
             frame: bool = True,
             limit: int | None = None,
             timeout: int | None = None) -> None:
        from ctrader_open_api import Protobuf
        sid = int(symbol)
        tf_id = _timeframe_id_(timeframe)
        tf_uid = _timeframe_uid_(tf_id)
        try:
            self.connect()
            counter = {"n": 0}
            done = threading.Event()
            def handler(message):
                if done.is_set(): return
                payload = Protobuf.extract(message)
                if type(payload).__name__ != _SPOT_EVENT_: return
                if int(payload.symbolId) != sid: return
                for bar in payload.trendbar:
                    if int(bar.period) != tf_id: continue
                    low = bar.low
                    data = {
                        "SecurityUID": sid,
                        "TimeframeUID": tf_uid,
                        "UtcTimestampInMinutes": int(bar.utcTimestampInMinutes),
                        "OpenBidPrice": (low + bar.deltaOpen) / _PRICE_SCALE_,
                        "HighBidPrice": (low + bar.deltaHigh) / _PRICE_SCALE_,
                        "LowBidPrice": low / _PRICE_SCALE_,
                        "CloseBidPrice": (low + bar.deltaClose) / _PRICE_SCALE_,
                        "TickVolume": int(bar.volume)
                    }
                    callback(self._api_.frame([data]) if frame else data)
                    counter["n"] += 1
                    if limit is not None and counter["n"] >= limit:
                        done.set()
                        return
            self._api_._subscribe_(handler)
            try:
                request = Protobuf.get("ProtoOASubscribeLiveTrendbarReq",
                                       ctidTraderAccountId=self._api_._account_id_,
                                       period=tf_id,
                                       symbolId=sid)
                self._api_._send_(request)
                done.wait(timeout=timeout)
            finally:
                self._api_._unsubscribe_(handler)
                try:
                    unsub = Protobuf.get("ProtoOAUnsubscribeLiveTrendbarReq",
                                         ctidTraderAccountId=self._api_._account_id_,
                                         period=tf_id,
                                         symbolId=sid)
                    self._api_._send_(unsub)
                except Exception: pass
        except KeyboardInterrupt:
            self._log_.info(lambda: "Bars Stream: Interrupted by User")
        except Exception as e:
            self._log_.error(lambda: "Bars Stream: Failed")
            self._log_.exception(lambda: str(e))
            raise

    def depth(self,
              symbols: int | list[int],
              callback: Callable,
              frame: bool = True,
              limit: int | None = None,
              timeout: int | None = None) -> None:
        from ctrader_open_api import Protobuf
        ids = [int(i) for i in self._api_.flatten(symbols)]
        try:
            self.connect()
            counter = {"n": 0}
            done = threading.Event()
            def handler(message):
                if done.is_set(): return
                payload = Protobuf.extract(message)
                if type(payload).__name__ != _DEPTH_EVENT_: return
                if int(payload.symbolId) not in ids: return
                rows = []
                for q in payload.newQuotes:
                    rows.append({
                        "SecurityUID": int(payload.symbolId),
                        "QuoteId": int(q.id),
                        "Size": int(q.size),
                        "BidPrice": (q.bid / _PRICE_SCALE_) if q.HasField("bid") else None,
                        "AskPrice": (q.ask / _PRICE_SCALE_) if q.HasField("ask") else None,
                        "Action": "New"
                    })
                for qid in payload.deletedQuotes:
                    rows.append({
                        "SecurityUID": int(payload.symbolId),
                        "QuoteId": int(qid),
                        "Size": None,
                        "BidPrice": None,
                        "AskPrice": None,
                        "Action": "Deleted"
                    })
                if not rows: return
                callback(self._api_.frame(rows) if frame else rows)
                counter["n"] += 1
                if limit is not None and counter["n"] >= limit: done.set()
            self._api_._subscribe_(handler)
            try:
                request = Protobuf.get("ProtoOASubscribeDepthQuotesReq",
                                       ctidTraderAccountId=self._api_._account_id_,
                                       symbolId=ids)
                self._api_._send_(request)
                done.wait(timeout=timeout)
            finally:
                self._api_._unsubscribe_(handler)
                try:
                    unsub = Protobuf.get("ProtoOAUnsubscribeDepthQuotesReq",
                                         ctidTraderAccountId=self._api_._account_id_,
                                         symbolId=ids)
                    self._api_._send_(unsub)
                except Exception: pass
        except KeyboardInterrupt:
            self._log_.info(lambda: "Depth Stream: Interrupted by User")
        except Exception as e:
            self._log_.error(lambda: "Depth Stream: Failed")
            self._log_.exception(lambda: str(e))
            raise
