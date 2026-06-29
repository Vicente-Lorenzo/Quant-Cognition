import threading
from typing import Union, Callable

from Library.Utility.Service import ServiceAPI
from Library.Market.Tick import TickAPI
from Library.Market.Bar import BarAPI
from Library.Spotware.Market import MarketAPI

class StreamingAPI(ServiceAPI):

    _SPOT_EVENT_ = "ProtoOASpotEvent"
    _DEPTH_EVENT_ = "ProtoOADepthEvent"

    def ticks(self,
              symbols: Union[int, list[int]],
              callback: Callable,
              frame: bool = False,
              limit: Union[int, None] = None,
              timeout: Union[int, None] = None) -> None:
        from ctrader_open_api import Protobuf
        ids = [int(i) for i in self._api_.flatten(symbols)]
        try:
            self.connect()
            counter = {"n": 0}
            done = threading.Event()
            def handler(message):
                if done.is_set(): return
                payload = Protobuf.extract(message)
                if type(payload).__name__ != self._SPOT_EVENT_: return
                if int(payload.symbolId) not in ids: return
                
                from Library.Utility.Datetime import timestamp_to_datetime
                from datetime import timezone
                
                dt = None
                if payload.HasField("timestamp"):
                    dt = timestamp_to_datetime(int(payload.timestamp), milliseconds=True).replace(tzinfo=timezone.utc)
                
                if payload.HasField("bid") or payload.HasField("ask"):
                    tick = TickAPI(
                        SecurityUID=int(payload.symbolId),
                        DateTime=dt,
                        AskPrice=(payload.ask / MarketAPI._PRICE_SCALE_) if payload.HasField("ask") else None,
                        BidPrice=(payload.bid / MarketAPI._PRICE_SCALE_) if payload.HasField("bid") else None,
                        db=self._api_._db_ if hasattr(self._api_, "_db_") else None
                    )
                    callback(self._api_.frame([tick]) if frame else tick)
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
             timeframe: Union[str, int],
             callback: Callable,
             frame: bool = False,
             limit: Union[int, None] = None,
             timeout: Union[int, None] = None) -> None:
        from ctrader_open_api import Protobuf
        sid = int(symbol)
        tf_id = MarketAPI._timeframe_id_(timeframe)
        tf_uid = MarketAPI._timeframe_uid_(tf_id)
        try:
            self.connect()
            counter = {"n": 0}
            done = threading.Event()
            def handler(message):
                if done.is_set(): return
                payload = Protobuf.extract(message)
                if type(payload).__name__ != self._SPOT_EVENT_: return
                if int(payload.symbolId) != sid: return
                for bar in payload.trendbar:
                    if int(bar.period) != tf_id: continue
                    low = bar.low
                    from Library.Utility.Datetime import timestamp_to_datetime
                    from datetime import timezone
                    ts = timestamp_to_datetime(int(bar.utcTimestampInMinutes) * 60, milliseconds=False).replace(tzinfo=timezone.utc)
                    b = BarAPI(
                        SecurityUID=sid,
                        TimeframeUID=tf_uid,
                        DateTime=ts,
                        OpenBidPrice=(low + bar.deltaOpen) / MarketAPI._PRICE_SCALE_,
                        HighBidPrice=(low + bar.deltaHigh) / MarketAPI._PRICE_SCALE_,
                        LowBidPrice=low / MarketAPI._PRICE_SCALE_,
                        CloseBidPrice=(low + bar.deltaClose) / MarketAPI._PRICE_SCALE_,
                        TickVolume=int(bar.volume),
                        db=self._api_._db_ if hasattr(self._api_, "_db_") else None
                    )
                    callback(self._api_.frame([b]) if frame else b)
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
              symbols: Union[int, list[int]],
              callback: Callable,
              frame: bool = False,
              limit: Union[int, None] = None,
              timeout: Union[int, None] = None) -> None:
        from ctrader_open_api import Protobuf
        ids = [int(i) for i in self._api_.flatten(symbols)]
        try:
            self.connect()
            counter = {"n": 0}
            done = threading.Event()
            def handler(message):
                if done.is_set(): return
                payload = Protobuf.extract(message)
                if type(payload).__name__ != self._DEPTH_EVENT_: return
                if int(payload.symbolId) not in ids: return
                rows = []
                for q in payload.newQuotes:
                    rows.append({
                        "SecurityUID": int(payload.symbolId),
                        "QuoteId": int(q.id),
                        "Size": int(q.size),
                        "BidPrice": (q.bid / MarketAPI._PRICE_SCALE_) if q.HasField("bid") else None,
                        "AskPrice": (q.ask / MarketAPI._PRICE_SCALE_) if q.HasField("ask") else None,
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