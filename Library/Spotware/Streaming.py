from typing import Callable, Union
from ctrader_open_api.messages.OpenApiModelMessages_pb2 import ProtoOATrendbarPeriod
from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOADepthEvent, ProtoOASpotEvent

from Library.Market.Tick import TickAPI
from Library.Utility.Service import ServiceAPI

class StreamingAPI(ServiceAPI):

    def ticks(self,
              symbols: Union[int, list[int]],
              callback: Callable,
              frame: bool = False,
              limit: Union[int, None] = None,
              timeout: Union[float, None] = None) -> int:
        ids = [int(i) for i in self._api_.flatten(symbols)]
        stamp, ask, bid = str(TickAPI.ID.Timestamp), str(TickAPI.ID.Ask), str(TickAPI.ID.Bid)
        def _decode_(payload) -> list:
            if not isinstance(payload, ProtoOASpotEvent) or payload.symbolId not in ids: return []
            if not (payload.HasField("bid") or payload.HasField("ask")): return []
            row = {
                "Symbol": int(payload.symbolId),
                stamp: self._api_._optional_(payload, "timestamp", self._api_._stamp_),
                ask: self._api_._optional_(payload, "ask", self._api_._price_),
                bid: self._api_._optional_(payload, "bid", self._api_._price_)
            }
            return [self._api_.frame([row]) if frame else row]
        subscribe = self._api_._message_("ProtoOASubscribeSpotsReq", symbolId=ids)
        unsubscribe = self._api_._message_("ProtoOAUnsubscribeSpotsReq", symbolId=ids)
        return self._api_._listen_(subscribe, unsubscribe, _decode_, callback, limit=limit, timeout=timeout)

    def bars(self,
             symbol: int,
             timeframe: Union[str, int],
             callback: Callable,
             frame: bool = False,
             limit: Union[int, None] = None,
             timeout: Union[float, None] = None) -> int:
        sid = int(symbol)
        period = self._api_.market._period_(timeframe)
        label = ProtoOATrendbarPeriod.Name(period)
        def _decode_(payload) -> list:
            if not isinstance(payload, ProtoOASpotEvent) or payload.symbolId != sid: return []
            rows = [self._api_.market._trendbar_(bar, sid, label) for bar in payload.trendbar if bar.period == period]
            return [self._api_.frame([row]) for row in rows] if frame else rows
        subscribe = self._api_._message_("ProtoOASubscribeLiveTrendbarReq", period=period, symbolId=sid)
        unsubscribe = self._api_._message_("ProtoOAUnsubscribeLiveTrendbarReq", period=period, symbolId=sid)
        return self._api_._listen_(subscribe, unsubscribe, _decode_, callback, limit=limit, timeout=timeout)

    def depth(self,
              symbols: Union[int, list[int]],
              callback: Callable,
              frame: bool = False,
              limit: Union[int, None] = None,
              timeout: Union[float, None] = None) -> int:
        ids = [int(i) for i in self._api_.flatten(symbols)]
        ask, bid = str(TickAPI.ID.Ask), str(TickAPI.ID.Bid)
        def _decode_(payload) -> list:
            if not isinstance(payload, ProtoOADepthEvent) or payload.symbolId not in ids: return []
            sid = int(payload.symbolId)
            rows = [{**self._api_.market._quote_(sid, quote), "Action": "New"} for quote in payload.newQuotes]
            rows += [{"Symbol": sid, "Quote": int(quote), "Size": None, bid: None, ask: None, "Action": "Deleted"} for quote in payload.deletedQuotes]
            if not rows: return []
            return [self._api_.frame(rows) if frame else rows]
        subscribe = self._api_._message_("ProtoOASubscribeDepthQuotesReq", symbolId=ids)
        unsubscribe = self._api_._message_("ProtoOAUnsubscribeDepthQuotesReq", symbolId=ids)
        return self._api_._listen_(subscribe, unsubscribe, _decode_, callback, limit=limit, timeout=timeout)