from typing import Union
from datetime import datetime
from functools import partialmethod
from collections.abc import Sequence
from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOAExecutionEvent, ProtoOAOrderErrorEvent
from ctrader_open_api.messages.OpenApiModelMessages_pb2 import ProtoOAOrderType, ProtoOATimeInForce, ProtoOATradeSide

from Library.Database.Dataframe import pd, pl
from Library.Portfolio.Order import TimeInForce
from Library.Utility.Service import ServiceAPI
from Library.Utility.Typing import MISSING, Missing

class ExecutionAPI(ServiceAPI):

    @staticmethod
    def _is_seq_(value) -> bool:
        return isinstance(value, Sequence) and not isinstance(value, (str, bytes))

    @classmethod
    def _broadcast_(cls, **kwargs) -> list[dict]:
        lengths = {len(v) for v in kwargs.values() if cls._is_seq_(v)}
        if not lengths: return [kwargs]
        if len(lengths) > 1: raise ValueError(f"Batch Operation: Failed · Mismatched lengths {sorted(lengths)}")
        n = lengths.pop()
        return [{k: (v[i] if cls._is_seq_(v) else v) for k, v in kwargs.items()} for i in range(n)]

    def _execution_(self, payload) -> dict:
        row = {"ResponseType": type(payload).__name__ if payload is not None else "", "ExecutionType": None, "OrderID": None, "PositionID": None, "DealID": None, "ErrorCode": None, "Description": None}
        if isinstance(payload, ProtoOAExecutionEvent):
            row["ExecutionType"] = self._api_._named_(payload, "executionType")
            if payload.HasField("order"): row["OrderID"] = payload.order.orderId
            if payload.HasField("position"): row["PositionID"] = payload.position.positionId
            if payload.HasField("deal"):
                row["DealID"] = payload.deal.dealId
                row["OrderID"] = row["OrderID"] or payload.deal.orderId
                row["PositionID"] = row["PositionID"] or payload.deal.positionId
            row["ErrorCode"] = self._api_._optional_(payload, "errorCode")
        elif isinstance(payload, ProtoOAOrderErrorEvent):
            row["ErrorCode"] = payload.errorCode
            row["OrderID"] = self._api_._optional_(payload, "orderId")
            row["PositionID"] = self._api_._optional_(payload, "positionId")
            row["Description"] = self._api_._optional_(payload, "description")
        return row

    def _order_(self,
                order_type: Union[str, int],
                side: Union[str, int],
                symbol: int,
                volume: float,
                *,
                limit_price: Union[float, None] = None,
                stop_price: Union[float, None] = None,
                base_slippage_price: Union[float, None] = None,
                slippage_points: Union[int, None] = None,
                stop_loss: Union[float, None] = None,
                take_profit: Union[float, None] = None,
                relative_stop_loss: Union[float, None, Missing] = MISSING,
                relative_take_profit: Union[float, None, Missing] = MISSING,
                time_in_force: Union[str, int, TimeInForce, None] = None,
                expiration: Union[datetime, None] = None,
                label: Union[str, None] = None,
                comment: Union[str, None] = None,
                client_order_id: Union[str, None] = None,
                position_id: Union[int, None] = None,
                trailing: bool = False,
                guaranteed: bool = False) -> dict:
        api = self._api_
        fields = {"symbolId": int(symbol), "orderType": api._code_(ProtoOAOrderType, order_type), "tradeSide": api._code_(ProtoOATradeSide, side), "volume": api._cents_(volume)}
        if limit_price is not None: fields["limitPrice"] = float(limit_price)
        if stop_price is not None: fields["stopPrice"] = float(stop_price)
        if base_slippage_price is not None: fields["baseSlippagePrice"] = float(base_slippage_price)
        if slippage_points is not None: fields["slippageInPoints"] = int(slippage_points)
        if stop_loss is not None: fields["stopLoss"] = float(stop_loss)
        if take_profit is not None: fields["takeProfit"] = float(take_profit)
        if relative_stop_loss is not None and relative_stop_loss is not MISSING: fields["relativeStopLoss"] = api._relative_(relative_stop_loss)
        if relative_take_profit is not None and relative_take_profit is not MISSING: fields["relativeTakeProfit"] = api._relative_(relative_take_profit)
        if time_in_force is not None: fields["timeInForce"] = api._code_(ProtoOATimeInForce, time_in_force)
        if expiration is not None: fields["expirationTimestamp"] = api._epoch_(expiration)
        if label is not None: fields["label"] = str(label)
        if comment is not None: fields["comment"] = str(comment)
        if client_order_id is not None: fields["clientOrderId"] = str(client_order_id)
        if position_id is not None: fields["positionId"] = int(position_id)
        if trailing: fields["trailingStopLoss"] = True
        if guaranteed: fields["guaranteedStopLoss"] = True
        return self._execution_(api._request_("ProtoOANewOrderReq", **fields))

    def _modify_order_(self,
                       order: int,
                       volume: Union[float, None] = None,
                       limit_price: Union[float, None] = None,
                       stop_price: Union[float, None] = None,
                       stop_loss: Union[float, None] = None,
                       take_profit: Union[float, None] = None,
                       expiration: Union[datetime, None] = None,
                       slippage_points: Union[int, None] = None,
                       trailing: Union[bool, None] = None,
                       guaranteed: Union[bool, None] = None) -> dict:
        api = self._api_
        fields = {"orderId": int(order)}
        if volume is not None: fields["volume"] = api._cents_(volume)
        if limit_price is not None: fields["limitPrice"] = float(limit_price)
        if stop_price is not None: fields["stopPrice"] = float(stop_price)
        if stop_loss is not None: fields["stopLoss"] = float(stop_loss)
        if take_profit is not None: fields["takeProfit"] = float(take_profit)
        if expiration is not None: fields["expirationTimestamp"] = api._epoch_(expiration)
        if slippage_points is not None: fields["slippageInPoints"] = int(slippage_points)
        if trailing is not None: fields["trailingStopLoss"] = bool(trailing)
        if guaranteed is not None: fields["guaranteedStopLoss"] = bool(guaranteed)
        return self._execution_(api._request_("ProtoOAAmendOrderReq", **fields))

    def _modify_position_(self,
                          position: int,
                          stop_loss: Union[float, None] = None,
                          take_profit: Union[float, None] = None,
                          trailing: Union[bool, None] = None,
                          guaranteed: Union[bool, None] = None) -> dict:
        fields = {"positionId": int(position)}
        if stop_loss is not None: fields["stopLoss"] = float(stop_loss)
        if take_profit is not None: fields["takeProfit"] = float(take_profit)
        if trailing is not None: fields["trailingStopLoss"] = bool(trailing)
        if guaranteed is not None: fields["guaranteedStopLoss"] = bool(guaranteed)
        return self._execution_(self._api_._request_("ProtoOAAmendPositionSLTPReq", **fields))

    def _close_order_(self, order: int) -> dict:
        return self._execution_(self._api_._request_("ProtoOACancelOrderReq", orderId=int(order)))

    def _close_position_(self, position: int, volume: float) -> dict:
        return self._execution_(self._api_._request_("ProtoOAClosePositionReq", positionId=int(position), volume=self._api_._cents_(volume)))

    def _resolve_orders_(self, order: Union[int, Sequence[int], None]) -> list[int]:
        if order is None:
            orders = self._api_.portfolio.orders(legacy=False)
            return [] if orders.is_empty() else orders["OrderID"].to_list()
        return [int(i) for i in order] if self._is_seq_(order) else [int(order)]

    def _resolve_positions_(self,
                            position: Union[int, Sequence[int], None],
                            volume: Union[float, Sequence[float], None]) -> list[tuple[int, float]]:
        if position is None:
            positions = self._api_.portfolio.positions(legacy=False)
            return [] if positions.is_empty() else list(zip(positions["PositionID"].to_list(), positions["Volume"].to_list()))
        ids = [int(i) for i in position] if self._is_seq_(position) else [int(position)]
        if volume is None:
            positions = self._api_.portfolio.positions(legacy=False)
            volumes = dict(zip(positions["PositionID"].to_list(), positions["Volume"].to_list()))
            return [(i, volumes[i]) for i in ids]
        if not self._is_seq_(volume): return [(i, volume) for i in ids]
        if len(volume) != len(ids): raise ValueError(f"Batch Operation: Failed · Mismatched lengths position ({len(ids)}) volume ({len(volume)})")
        return list(zip(ids, volume))

    def _place_(self, operation: str, order_type: str, batches: list[dict], legacy: Union[bool, Missing]) -> Union[pd.DataFrame, pl.DataFrame]:
        timer, result = super()._fetch_(callback=lambda: self._api_.frame([self._order_(order_type, **batch) for batch in batches], legacy=legacy))
        self._log_.info(lambda: f"{operation} Operation: Placed {len(result)} orders ({timer.result()})")
        return result

    def market_order(self,
                     side: Union[str, int, Sequence[Union[str, int]]],
                     symbol: Union[int, Sequence[int]],
                     volume: Union[float, Sequence[float]],
                     relative_stop_loss: Union[float, Sequence[float], None, Missing] = MISSING,
                     relative_take_profit: Union[float, Sequence[float], None, Missing] = MISSING,
                     label: Union[str, Sequence[str], None] = None,
                     comment: Union[str, Sequence[str], None] = None,
                     client_order_id: Union[str, Sequence[str], None] = None,
                     trailing: Union[bool, Sequence[bool]] = False,
                     guaranteed: Union[bool, Sequence[bool]] = False,
                     legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame]:
        batches = self._broadcast_(side=side, symbol=symbol, volume=volume, relative_stop_loss=relative_stop_loss, relative_take_profit=relative_take_profit, label=label, comment=comment, client_order_id=client_order_id, trailing=trailing, guaranteed=guaranteed)
        return self._place_("Market Order", "Market", batches, legacy)

    def range_order(self,
                    side: Union[str, int, Sequence[Union[str, int]]],
                    symbol: Union[int, Sequence[int]],
                    volume: Union[float, Sequence[float]],
                    base_price: Union[float, Sequence[float]],
                    slippage_points: Union[int, Sequence[int]],
                    relative_stop_loss: Union[float, Sequence[float], None, Missing] = MISSING,
                    relative_take_profit: Union[float, Sequence[float], None, Missing] = MISSING,
                    label: Union[str, Sequence[str], None] = None,
                    comment: Union[str, Sequence[str], None] = None,
                    client_order_id: Union[str, Sequence[str], None] = None,
                    trailing: Union[bool, Sequence[bool]] = False,
                    guaranteed: Union[bool, Sequence[bool]] = False,
                    legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame]:
        batches = self._broadcast_(side=side, symbol=symbol, volume=volume, base_slippage_price=base_price, slippage_points=slippage_points, relative_stop_loss=relative_stop_loss, relative_take_profit=relative_take_profit, label=label, comment=comment, client_order_id=client_order_id, trailing=trailing, guaranteed=guaranteed)
        return self._place_("Range Order", "MarketRange", batches, legacy)

    def limit_order(self,
                    side: Union[str, int, Sequence[Union[str, int]]],
                    symbol: Union[int, Sequence[int]],
                    volume: Union[float, Sequence[float]],
                    price: Union[float, Sequence[float]],
                    stop_loss: Union[float, Sequence[float], None] = None,
                    take_profit: Union[float, Sequence[float], None] = None,
                    time_in_force: Union[str, int, TimeInForce, Sequence[Union[str, int, TimeInForce]], None] = TimeInForce.GoodTillCancel,
                    expiration: Union[datetime, Sequence[datetime], None] = None,
                    label: Union[str, Sequence[str], None] = None,
                    comment: Union[str, Sequence[str], None] = None,
                    client_order_id: Union[str, Sequence[str], None] = None,
                    trailing: Union[bool, Sequence[bool]] = False,
                    guaranteed: Union[bool, Sequence[bool]] = False,
                    legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame]:
        batches = self._broadcast_(side=side, symbol=symbol, volume=volume, limit_price=price, stop_loss=stop_loss, take_profit=take_profit, time_in_force=time_in_force, expiration=expiration, label=label, comment=comment, client_order_id=client_order_id, trailing=trailing, guaranteed=guaranteed)
        return self._place_("Limit Order", "Limit", batches, legacy)

    def stop_order(self,
                   side: Union[str, int, Sequence[Union[str, int]]],
                   symbol: Union[int, Sequence[int]],
                   volume: Union[float, Sequence[float]],
                   price: Union[float, Sequence[float]],
                   stop_loss: Union[float, Sequence[float], None] = None,
                   take_profit: Union[float, Sequence[float], None] = None,
                   time_in_force: Union[str, int, TimeInForce, Sequence[Union[str, int, TimeInForce]], None] = TimeInForce.GoodTillCancel,
                   expiration: Union[datetime, Sequence[datetime], None] = None,
                   slippage_points: Union[int, Sequence[int], None] = None,
                   label: Union[str, Sequence[str], None] = None,
                   comment: Union[str, Sequence[str], None] = None,
                   client_order_id: Union[str, Sequence[str], None] = None,
                   trailing: Union[bool, Sequence[bool]] = False,
                   guaranteed: Union[bool, Sequence[bool]] = False,
                   legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame]:
        batches = self._broadcast_(side=side, symbol=symbol, volume=volume, stop_price=price, stop_loss=stop_loss, take_profit=take_profit, time_in_force=time_in_force, expiration=expiration, slippage_points=slippage_points, label=label, comment=comment, client_order_id=client_order_id, trailing=trailing, guaranteed=guaranteed)
        return self._place_("Stop Order", "Stop", batches, legacy)

    def stop_limit_order(self,
                         side: Union[str, int, Sequence[Union[str, int]]],
                         symbol: Union[int, Sequence[int]],
                         volume: Union[float, Sequence[float]],
                         stop_price: Union[float, Sequence[float]],
                         limit_price: Union[float, Sequence[float]],
                         stop_loss: Union[float, Sequence[float], None] = None,
                         take_profit: Union[float, Sequence[float], None] = None,
                         time_in_force: Union[str, int, TimeInForce, Sequence[Union[str, int, TimeInForce]], None] = TimeInForce.GoodTillCancel,
                         expiration: Union[datetime, Sequence[datetime], None] = None,
                         label: Union[str, Sequence[str], None] = None,
                         comment: Union[str, Sequence[str], None] = None,
                         client_order_id: Union[str, Sequence[str], None] = None,
                         trailing: Union[bool, Sequence[bool]] = False,
                         guaranteed: Union[bool, Sequence[bool]] = False,
                         legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame]:
        batches = self._broadcast_(side=side, symbol=symbol, volume=volume, stop_price=stop_price, limit_price=limit_price, stop_loss=stop_loss, take_profit=take_profit, time_in_force=time_in_force, expiration=expiration, label=label, comment=comment, client_order_id=client_order_id, trailing=trailing, guaranteed=guaranteed)
        return self._place_("Stop Limit Order", "StopLimit", batches, legacy)

    market_buy_order = partialmethod(market_order, side="Buy")
    market_sell_order = partialmethod(market_order, side="Sell")
    range_buy_order = partialmethod(range_order, side="Buy")
    range_sell_order = partialmethod(range_order, side="Sell")
    limit_buy_order = partialmethod(limit_order, side="Buy")
    limit_sell_order = partialmethod(limit_order, side="Sell")
    stop_buy_order = partialmethod(stop_order, side="Buy")
    stop_sell_order = partialmethod(stop_order, side="Sell")
    stop_limit_buy_order = partialmethod(stop_limit_order, side="Buy")
    stop_limit_sell_order = partialmethod(stop_limit_order, side="Sell")

    def modify_order(self,
                     order: Union[int, Sequence[int]],
                     volume: Union[float, Sequence[float], None] = None,
                     limit_price: Union[float, Sequence[float], None] = None,
                     stop_price: Union[float, Sequence[float], None] = None,
                     stop_loss: Union[float, Sequence[float], None] = None,
                     take_profit: Union[float, Sequence[float], None] = None,
                     expiration: Union[datetime, Sequence[datetime], None] = None,
                     slippage_points: Union[int, Sequence[int], None] = None,
                     trailing: Union[bool, Sequence[bool], None] = None,
                     guaranteed: Union[bool, Sequence[bool], None] = None,
                     legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame]:
        batches = self._broadcast_(order=order, volume=volume, limit_price=limit_price, stop_price=stop_price, stop_loss=stop_loss, take_profit=take_profit, expiration=expiration, slippage_points=slippage_points, trailing=trailing, guaranteed=guaranteed)
        timer, result = super()._fetch_(callback=lambda: self._api_.frame([self._modify_order_(**batch) for batch in batches], legacy=legacy))
        self._log_.info(lambda: f"Modify Order Operation: Modified {len(result)} orders ({timer.result()})")
        return result

    def close_order(self,
                    order: Union[int, Sequence[int], None] = None,
                    legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame]:
        timer, result = super()._fetch_(callback=lambda: self._api_.frame([self._close_order_(order=i) for i in self._resolve_orders_(order)], legacy=legacy))
        self._log_.info(lambda: f"Close Order Operation: Cancelled {len(result)} orders ({timer.result()})")
        return result

    def modify_position(self,
                        position: Union[int, Sequence[int]],
                        stop_loss: Union[float, Sequence[float], None] = None,
                        take_profit: Union[float, Sequence[float], None] = None,
                        trailing: Union[bool, Sequence[bool], None] = None,
                        guaranteed: Union[bool, Sequence[bool], None] = None,
                        legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame]:
        batches = self._broadcast_(position=position, stop_loss=stop_loss, take_profit=take_profit, trailing=trailing, guaranteed=guaranteed)
        timer, result = super()._fetch_(callback=lambda: self._api_.frame([self._modify_position_(**batch) for batch in batches], legacy=legacy))
        self._log_.info(lambda: f"Modify Position Operation: Modified {len(result)} positions ({timer.result()})")
        return result

    def close_position(self,
                       position: Union[int, Sequence[int], None] = None,
                       volume: Union[float, Sequence[float], None] = None,
                       legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame]:
        timer, result = super()._fetch_(callback=lambda: self._api_.frame([self._close_position_(position=i, volume=v) for i, v in self._resolve_positions_(position, volume)], legacy=legacy))
        self._log_.info(lambda: f"Close Position Operation: Closed {len(result)} positions ({timer.result()})")
        return result