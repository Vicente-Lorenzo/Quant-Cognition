from typing import Union
from collections.abc import Sequence
from datetime import datetime

from Library.Database.Dataframe import pd, pl
from Library.Utility.Service import ServiceAPI
from Library.Utility.Typing import MISSING, Missing
from Library.Portfolio.Order import OrderAPI

class ExecutionAPI(ServiceAPI):

    _SIDE_MAP_ = {"BUY": 1, "SELL": 2}
    _ORDER_TYPE_MAP_ = {"MARKET": 1, "LIMIT": 2, "STOP": 3, "STOP_LOSS_TAKE_PROFIT": 4, "MARKET_RANGE": 5, "STOP_LIMIT": 6}
    _TIME_IN_FORCE_MAP_ = {"GTD": 1, "GTC": 2, "IOC": 3, "FOK": 4, "MOO": 5,
                           "GOOD_TILL_DATE": 1, "GOOD_TILL_CANCEL": 2,
                           "IMMEDIATE_OR_CANCEL": 3, "FILL_OR_KILL": 4, "MARKET_ON_OPEN": 5}

    @classmethod
    def _side_(cls, value: Union[str, int]) -> int:
        if isinstance(value, int): return value
        return cls._SIDE_MAP_[str(value).upper()]

    @classmethod
    def _order_type_(cls, value: Union[str, int]) -> int:
        if isinstance(value, int): return value
        return cls._ORDER_TYPE_MAP_[str(value).upper()]

    @classmethod
    def _tif_(cls, value: Union[str, int, None]) -> Union[int, None]:
        if value is None: return None
        if isinstance(value, int): return value
        return cls._TIME_IN_FORCE_MAP_[str(value).upper()]

    @staticmethod
    def _is_seq_(value) -> bool:
        return isinstance(value, Sequence) and not isinstance(value, (str, bytes))

    @classmethod
    def _broadcast_(cls, **kwargs) -> list[dict]:
        lengths = {len(v) for v in kwargs.values() if cls._is_seq_(v)}
        if not lengths: return [kwargs]
        if len(lengths) > 1: raise ValueError(f"Mismatched batch lengths: {sorted(lengths)}")
        n = lengths.pop()
        return [{k: (v[i] if cls._is_seq_(v) else v) for k, v in kwargs.items()} for i in range(n)]

    def market_order(self,
                     side: Union[str, int, Sequence[str, int]],
                     symbol: Union[int, Sequence[int]],
                     volume: Union[int, Sequence[int]],
                     stop_loss: Union[float, Sequence[float], None] = None,
                     take_profit: Union[float, Sequence[float], None] = None,
                     label: Union[str, Sequence[str], None] = None,
                     comment: Union[str, Sequence[str], None] = None,
                     client_order_id: Union[str, Sequence[str], None] = None,
                     trailing: Union[bool, Sequence[bool]] = False,
                     guaranteed: Union[bool, Sequence[bool]] = False,
                     legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame, list[dict]]:
        batches = self._broadcast_(
            side=side,
            symbol=symbol,
            volume=volume,
            stop_loss=stop_loss,
            take_profit=take_profit,
            label=label,
            comment=comment,
            client_order_id=client_order_id,
            trailing=trailing,
            guaranteed=guaranteed)
        def _fetch_():
            rows = [self._order_(order_type="MARKET", **p) for p in batches]
            if legacy is MISSING: return rows
            return self._api_.frame(rows, legacy=legacy)
        timer, result = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Market Order Operation: Placed {len(result)} orders ({timer.result()})")
        return result

    def market_buy_order(self,
                         symbol: Union[int, Sequence[int]],
                         volume: Union[int, Sequence[int]],
                         stop_loss: Union[float, Sequence[float], None] = None,
                         take_profit: Union[float, Sequence[float], None] = None,
                         label: Union[str, Sequence[str], None] = None,
                         comment: Union[str, Sequence[str], None] = None,
                         client_order_id: Union[str, Sequence[str], None] = None,
                         trailing: Union[bool, Sequence[bool]] = False,
                         guaranteed: Union[bool, Sequence[bool]] = False,
                         legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame, list[dict]]:
        return self.market_order(
            side="BUY",
            symbol=symbol,
            volume=volume,
            stop_loss=stop_loss,
            take_profit=take_profit,
            label=label,
            comment=comment,
            client_order_id=client_order_id,
            trailing=trailing,
            guaranteed=guaranteed,
            legacy=legacy)

    def market_sell_order(self,
                          symbol: Union[int, Sequence[int]],
                          volume: Union[int, Sequence[int]],
                          stop_loss: Union[float, Sequence[float], None] = None,
                          take_profit: Union[float, Sequence[float], None] = None,
                          label: Union[str, Sequence[str], None] = None,
                          comment: Union[str, Sequence[str], None] = None,
                          client_order_id: Union[str, Sequence[str], None] = None,
                          trailing: Union[bool, Sequence[bool]] = False,
                          guaranteed: Union[bool, Sequence[bool]] = False,
                          legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame, list[dict]]:
        return self.market_order(
            side="SELL",
            symbol=symbol,
            volume=volume,
            stop_loss=stop_loss,
            take_profit=take_profit,
            label=label,
            comment=comment,
            client_order_id=client_order_id,
            trailing=trailing,
            guaranteed=guaranteed,
            legacy=legacy)

    def range_order(self,
                    side: Union[str, int, Sequence[str, int]],
                    symbol: Union[int, Sequence[int]],
                    volume: Union[int, Sequence[int]],
                    base_price: Union[float, Sequence[float]],
                    slippage_points: Union[int, Sequence[int]],
                    stop_loss: Union[float, Sequence[float], None] = None,
                    take_profit: Union[float, Sequence[float], None] = None,
                    label: Union[str, Sequence[str], None] = None,
                    comment: Union[str, Sequence[str], None] = None,
                    client_order_id: Union[str, Sequence[str], None] = None,
                    trailing: Union[bool, Sequence[bool]] = False,
                    guaranteed: Union[bool, Sequence[bool]] = False,
                    legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame, list[dict]]:
        batches = self._broadcast_(
            side=side,
            symbol=symbol,
            volume=volume,
            base_slippage_price=base_price,
            slippage_points=slippage_points,
            stop_loss=stop_loss,
            take_profit=take_profit,
            label=label,
            comment=comment,
            client_order_id=client_order_id,
            trailing=trailing,
            guaranteed=guaranteed)
        def _fetch_():
            rows = [self._order_(order_type="MARKET_RANGE", **p) for p in batches]
            if legacy is MISSING: return rows
            return self._api_.frame(rows, legacy=legacy)
        timer, result = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Range Order Operation: Placed {len(result)} orders ({timer.result()})")
        return result

    def range_buy_order(self,
                        symbol: Union[int, Sequence[int]],
                        volume: Union[int, Sequence[int]],
                        base_price: Union[float, Sequence[float]],
                        slippage_points: Union[int, Sequence[int]],
                        stop_loss: Union[float, Sequence[float], None] = None,
                        take_profit: Union[float, Sequence[float], None] = None,
                        label: Union[str, Sequence[str], None] = None,
                        comment: Union[str, Sequence[str], None] = None,
                        client_order_id: Union[str, Sequence[str], None] = None,
                        trailing: Union[bool, Sequence[bool]] = False,
                        guaranteed: Union[bool, Sequence[bool]] = False,
                        legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame, list[dict]]:
        return self.range_order(
            side="BUY",
            symbol=symbol,
            volume=volume,
            base_price=base_price,
            slippage_points=slippage_points,
            stop_loss=stop_loss,
            take_profit=take_profit,
            label=label,
            comment=comment,
            client_order_id=client_order_id,
            trailing=trailing,
            guaranteed=guaranteed,
            legacy=legacy)

    def range_sell_order(self,
                         symbol: Union[int, Sequence[int]],
                         volume: Union[int, Sequence[int]],
                         base_price: Union[float, Sequence[float]],
                         slippage_points: Union[int, Sequence[int]],
                         stop_loss: Union[float, Sequence[float], None] = None,
                         take_profit: Union[float, Sequence[float], None] = None,
                         label: Union[str, Sequence[str], None] = None,
                         comment: Union[str, Sequence[str], None] = None,
                         client_order_id: Union[str, Sequence[str], None] = None,
                         trailing: Union[bool, Sequence[bool]] = False,
                         guaranteed: Union[bool, Sequence[bool]] = False,
                         legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame, list[dict]]:
        return self.range_order(
            side="SELL",
            symbol=symbol,
            volume=volume,
            base_price=base_price,
            slippage_points=slippage_points,
            stop_loss=stop_loss,
            take_profit=take_profit,
            label=label,
            comment=comment,
            client_order_id=client_order_id,
            trailing=trailing,
            guaranteed=guaranteed,
            legacy=legacy)

    def limit_order(self,
                    side: Union[str, int, Sequence[str, int]],
                    symbol: Union[int, Sequence[int]],
                    volume: Union[int, Sequence[int]],
                    price: Union[float, Sequence[float]],
                    stop_loss: Union[float, Sequence[float], None] = None,
                    take_profit: Union[float, Sequence[float], None] = None,
                    time_in_force: Union[str, int, Sequence[str, int], None] = "GTC",
                    expiration: Union[datetime, Sequence[datetime], None] = None,
                    label: Union[str, Sequence[str], None] = None,
                    comment: Union[str, Sequence[str], None] = None,
                    client_order_id: Union[str, Sequence[str], None] = None,
                    trailing: Union[bool, Sequence[bool]] = False,
                    guaranteed: Union[bool, Sequence[bool]] = False,
                    legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame, list[dict]]:
        batches = self._broadcast_(
            side=side,
            symbol=symbol,
            volume=volume,
            limit_price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            time_in_force=time_in_force,
            expiration=expiration,
            label=label,
            comment=comment,
            client_order_id=client_order_id,
            trailing=trailing,
            guaranteed=guaranteed)
        def _fetch_():
            rows = [self._order_(order_type="LIMIT", **p) for p in batches]
            if legacy is MISSING: return rows
            return self._api_.frame(rows, legacy=legacy)
        timer, result = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Limit Order Operation: Placed {len(result)} orders ({timer.result()})")
        return result

    def limit_buy_order(self,
                        symbol: Union[int, Sequence[int]],
                        volume: Union[int, Sequence[int]],
                        price: Union[float, Sequence[float]],
                        stop_loss: Union[float, Sequence[float], None] = None,
                        take_profit: Union[float, Sequence[float], None] = None,
                        time_in_force: Union[str, int, Sequence[str, int], None] = "GTC",
                        expiration: Union[datetime, Sequence[datetime], None] = None,
                        label: Union[str, Sequence[str], None] = None,
                        comment: Union[str, Sequence[str], None] = None,
                        client_order_id: Union[str, Sequence[str], None] = None,
                        trailing: Union[bool, Sequence[bool]] = False,
                        guaranteed: Union[bool, Sequence[bool]] = False,
                        legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame, list[dict]]:
        return self.limit_order(
            side="BUY",
            symbol=symbol,
            volume=volume,
            price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            time_in_force=time_in_force,
            expiration=expiration,
            label=label,
            comment=comment,
            client_order_id=client_order_id,
            trailing=trailing,
            guaranteed=guaranteed,
            legacy=legacy)

    def limit_sell_order(self,
                         symbol: Union[int, Sequence[int]],
                         volume: Union[int, Sequence[int]],
                         price: Union[float, Sequence[float]],
                         stop_loss: Union[float, Sequence[float], None] = None,
                         take_profit: Union[float, Sequence[float], None] = None,
                         time_in_force: Union[str, int, Sequence[str, int], None] = "GTC",
                         expiration: Union[datetime, Sequence[datetime], None] = None,
                         label: Union[str, Sequence[str], None] = None,
                         comment: Union[str, Sequence[str], None] = None,
                         client_order_id: Union[str, Sequence[str], None] = None,
                         trailing: Union[bool, Sequence[bool]] = False,
                         guaranteed: Union[bool, Sequence[bool]] = False,
                         legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame, list[dict]]:
        return self.limit_order(
            side="SELL",
            symbol=symbol,
            volume=volume,
            price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            time_in_force=time_in_force,
            expiration=expiration,
            label=label,
            comment=comment,
            client_order_id=client_order_id,
            trailing=trailing,
            guaranteed=guaranteed,
            legacy=legacy)

    def stop_order(self,
                   side: Union[str, int, Sequence[str, int]],
                   symbol: Union[int, Sequence[int]],
                   volume: Union[int, Sequence[int]],
                   price: Union[float, Sequence[float]],
                   stop_loss: Union[float, Sequence[float], None] = None,
                   take_profit: Union[float, Sequence[float], None] = None,
                   time_in_force: Union[str, int, Sequence[str, int], None] = "GTC",
                   expiration: Union[datetime, Sequence[datetime], None] = None,
                   slippage_points: Union[int, Sequence[int], None] = None,
                   label: Union[str, Sequence[str], None] = None,
                   comment: Union[str, Sequence[str], None] = None,
                   client_order_id: Union[str, Sequence[str], None] = None,
                   trailing: Union[bool, Sequence[bool]] = False,
                   guaranteed: Union[bool, Sequence[bool]] = False,
                   legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame, list[dict]]:
        batches = self._broadcast_(
            side=side,
            symbol=symbol,
            volume=volume,
            stop_price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            time_in_force=time_in_force,
            expiration=expiration,
            slippage_points=slippage_points,
            label=label,
            comment=comment,
            client_order_id=client_order_id,
            trailing=trailing,
            guaranteed=guaranteed)
        def _fetch_():
            rows = [self._order_(order_type="STOP", **p) for p in batches]
            if legacy is MISSING: return rows
            return self._api_.frame(rows, legacy=legacy)
        timer, result = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Stop Order Operation: Placed {len(result)} orders ({timer.result()})")
        return result

    def stop_buy_order(self,
                       symbol: Union[int, Sequence[int]],
                       volume: Union[int, Sequence[int]],
                       price: Union[float, Sequence[float]],
                       stop_loss: Union[float, Sequence[float], None] = None,
                       take_profit: Union[float, Sequence[float], None] = None,
                       time_in_force: Union[str, int, Sequence[str, int], None] = "GTC",
                       expiration: Union[datetime, Sequence[datetime], None] = None,
                       slippage_points: Union[int, Sequence[int], None] = None,
                       label: Union[str, Sequence[str], None] = None,
                       comment: Union[str, Sequence[str], None] = None,
                       client_order_id: Union[str, Sequence[str], None] = None,
                       trailing: Union[bool, Sequence[bool]] = False,
                       guaranteed: Union[bool, Sequence[bool]] = False,
                       legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame, list[dict]]:
        return self.stop_order(
            side="BUY",
            symbol=symbol,
            volume=volume,
            price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            time_in_force=time_in_force,
            expiration=expiration,
            slippage_points=slippage_points,
            label=label,
            comment=comment,
            client_order_id=client_order_id,
            trailing=trailing,
            guaranteed=guaranteed,
            legacy=legacy)

    def stop_sell_order(self,
                        symbol: Union[int, Sequence[int]],
                        volume: Union[int, Sequence[int]],
                        price: Union[float, Sequence[float]],
                        stop_loss: Union[float, Sequence[float], None] = None,
                        take_profit: Union[float, Sequence[float], None] = None,
                        time_in_force: Union[str, int, Sequence[str, int], None] = "GTC",
                        expiration: Union[datetime, Sequence[datetime], None] = None,
                        slippage_points: Union[int, Sequence[int], None] = None,
                        label: Union[str, Sequence[str], None] = None,
                        comment: Union[str, Sequence[str], None] = None,
                        client_order_id: Union[str, Sequence[str], None] = None,
                        trailing: Union[bool, Sequence[bool]] = False,
                        guaranteed: Union[bool, Sequence[bool]] = False,
                        legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame, list[dict]]:
        return self.stop_order(
            side="SELL",
            symbol=symbol,
            volume=volume,
            price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            time_in_force=time_in_force,
            expiration=expiration,
            slippage_points=slippage_points,
            label=label,
            comment=comment,
            client_order_id=client_order_id,
            trailing=trailing,
            guaranteed=guaranteed,
            legacy=legacy)

    def stop_limit_order(self,
                         side: Union[str, int, Sequence[str, int]],
                         symbol: Union[int, Sequence[int]],
                         volume: Union[int, Sequence[int]],
                         stop_price: Union[float, Sequence[float]],
                         limit_price: Union[float, Sequence[float]],
                         stop_loss: Union[float, Sequence[float], None] = None,
                         take_profit: Union[float, Sequence[float], None] = None,
                         time_in_force: Union[str, int, Sequence[str, int], None] = "GTC",
                         expiration: Union[datetime, Sequence[datetime], None] = None,
                         label: Union[str, Sequence[str], None] = None,
                         comment: Union[str, Sequence[str], None] = None,
                         client_order_id: Union[str, Sequence[str], None] = None,
                         trailing: Union[bool, Sequence[bool]] = False,
                         guaranteed: Union[bool, Sequence[bool]] = False,
                         legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame, list[dict]]:
        batches = self._broadcast_(
            side=side,
            symbol=symbol,
            volume=volume,
            stop_price=stop_price,
            limit_price=limit_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            time_in_force=time_in_force,
            expiration=expiration,
            label=label,
            comment=comment,
            client_order_id=client_order_id,
            trailing=trailing,
            guaranteed=guaranteed)
        def _fetch_():
            rows = [self._order_(order_type="STOP_LIMIT", **p) for p in batches]
            if legacy is MISSING: return rows
            return self._api_.frame(rows, legacy=legacy)
        timer, result = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Stop Limit Order Operation: Placed {len(result)} orders ({timer.result()})")
        return result

    def stop_limit_buy_order(self,
                             symbol: Union[int, Sequence[int]],
                             volume: Union[int, Sequence[int]],
                             stop_price: Union[float, Sequence[float]],
                             limit_price: Union[float, Sequence[float]],
                             stop_loss: Union[float, Sequence[float], None] = None,
                             take_profit: Union[float, Sequence[float], None] = None,
                             time_in_force: Union[str, int, Sequence[str, int], None] = "GTC",
                             expiration: Union[datetime, Sequence[datetime], None] = None,
                             label: Union[str, Sequence[str], None] = None,
                             comment: Union[str, Sequence[str], None] = None,
                             client_order_id: Union[str, Sequence[str], None] = None,
                             trailing: Union[bool, Sequence[bool]] = False,
                             guaranteed: Union[bool, Sequence[bool]] = False,
                             legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame, list[dict]]:
        return self.stop_limit_order(
            side="BUY",
            symbol=symbol,
            volume=volume,
            stop_price=stop_price,
            limit_price=limit_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            time_in_force=time_in_force,
            expiration=expiration,
            label=label,
            comment=comment,
            client_order_id=client_order_id,
            trailing=trailing,
            guaranteed=guaranteed,
            legacy=legacy)

    def stop_limit_sell_order(self,
                              symbol: Union[int, Sequence[int]],
                              volume: Union[int, Sequence[int]],
                              stop_price: Union[float, Sequence[float]],
                              limit_price: Union[float, Sequence[float]],
                              stop_loss: Union[float, Sequence[float], None] = None,
                              take_profit: Union[float, Sequence[float], None] = None,
                              time_in_force: Union[str, int, Sequence[str, int], None] = "GTC",
                              expiration: Union[datetime, Sequence[datetime], None] = None,
                              label: Union[str, Sequence[str], None] = None,
                              comment: Union[str, Sequence[str], None] = None,
                              client_order_id: Union[str, Sequence[str], None] = None,
                              trailing: Union[bool, Sequence[bool]] = False,
                              guaranteed: Union[bool, Sequence[bool]] = False,
                              legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame, list[dict]]:
        return self.stop_limit_order(
            side="SELL",
            symbol=symbol,
            volume=volume,
            stop_price=stop_price,
            limit_price=limit_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            time_in_force=time_in_force,
            expiration=expiration,
            label=label,
            comment=comment,
            client_order_id=client_order_id,
            trailing=trailing,
            guaranteed=guaranteed,
            legacy=legacy)

    def modify_order(self,
                     order: Union[int, Sequence[int]],
                     volume: Union[int, Sequence[int], None] = None,
                     limit_price: Union[float, Sequence[float], None] = None,
                     stop_price: Union[float, Sequence[float], None] = None,
                     stop_loss: Union[float, Sequence[float], None] = None,
                     take_profit: Union[float, Sequence[float], None] = None,
                     expiration: Union[datetime, Sequence[datetime], None] = None,
                     slippage_points: Union[int, Sequence[int], None] = None,
                     trailing: Union[bool, Sequence[bool], None] = None,
                     guaranteed: Union[bool, Sequence[bool], None] = None,
                     legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame, list[dict]]:
        batches = self._broadcast_(
            order=order,
            volume=volume,
            limit_price=limit_price,
            stop_price=stop_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            expiration=expiration,
            slippage_points=slippage_points,
            trailing=trailing,
            guaranteed=guaranteed)
        def _fetch_():
            rows = [self._modify_order_(**p) for p in batches]
            if legacy is MISSING: return rows
            return self._api_.frame(rows, legacy=legacy)
        timer, result = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Modify Order Operation: Modified {len(result)} orders ({timer.result()})")
        return result

    def modify_buy_order(self,
                         order: Union[int, Sequence[int]],
                         volume: Union[int, Sequence[int], None] = None,
                         limit_price: Union[float, Sequence[float], None] = None,
                         stop_price: Union[float, Sequence[float], None] = None,
                         stop_loss: Union[float, Sequence[float], None] = None,
                         take_profit: Union[float, Sequence[float], None] = None,
                         expiration: Union[datetime, Sequence[datetime], None] = None,
                         slippage_points: Union[int, Sequence[int], None] = None,
                         trailing: Union[bool, Sequence[bool], None] = None,
                         guaranteed: Union[bool, Sequence[bool], None] = None,
                         legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame, list[dict]]:
        return self.modify_order(
            order=order,
            volume=volume,
            limit_price=limit_price,
            stop_price=stop_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            expiration=expiration,
            slippage_points=slippage_points,
            trailing=trailing,
            guaranteed=guaranteed,
            legacy=legacy)

    def modify_sell_order(self,
                          order: Union[int, Sequence[int]],
                          volume: Union[int, Sequence[int], None] = None,
                          limit_price: Union[float, Sequence[float], None] = None,
                          stop_price: Union[float, Sequence[float], None] = None,
                          stop_loss: Union[float, Sequence[float], None] = None,
                          take_profit: Union[float, Sequence[float], None] = None,
                          expiration: Union[datetime, Sequence[datetime], None] = None,
                          slippage_points: Union[int, Sequence[int], None] = None,
                          trailing: Union[bool, Sequence[bool], None] = None,
                          guaranteed: Union[bool, Sequence[bool], None] = None,
                          legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame, list[dict]]:
        return self.modify_order(
            order=order,
            volume=volume,
            limit_price=limit_price,
            stop_price=stop_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            expiration=expiration,
            slippage_points=slippage_points,
            trailing=trailing,
            guaranteed=guaranteed,
            legacy=legacy)

    def close_order(self,
                    order: Union[int, Sequence[int], None] = None,
                    legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame, list[dict]]:
        def _fetch_():
            ids = self._resolve_orders_(order)
            rows = [self._close_order_(order=i) for i in ids]
            if legacy is MISSING: return rows
            return self._api_.frame(rows, legacy=legacy)
        timer, result = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Close Order Operation: Cancelled {len(result)} orders ({timer.result()})")
        return result

    def close_buy_order(self,
                        order: Union[int, Sequence[int], None] = None,
                        legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame, list[dict]]:
        return self.close_order(
            order=order,
            legacy=legacy)

    def close_sell_order(self,
                         order: Union[int, Sequence[int], None] = None,
                         legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame, list[dict]]:
        return self.close_order(
            order=order,
            legacy=legacy)

    def modify_position(self,
                        position: Union[int, Sequence[int]],
                        stop_loss: Union[float, Sequence[float], None] = None,
                        take_profit: Union[float, Sequence[float], None] = None,
                        trailing: Union[bool, Sequence[bool], None] = None,
                        guaranteed: Union[bool, Sequence[bool], None] = None,
                        legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame, list[dict]]:
        batches = self._broadcast_(
            position=position,
            stop_loss=stop_loss,
            take_profit=take_profit,
            trailing=trailing,
            guaranteed=guaranteed)
        def _fetch_():
            rows = [self._modify_position_(**p) for p in batches]
            if legacy is MISSING: return rows
            return self._api_.frame(rows, legacy=legacy)
        timer, result = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Modify Position Operation: Modified {len(result)} positions ({timer.result()})")
        return result

    def modify_buy_position(self,
                            position: Union[int, Sequence[int]],
                            stop_loss: Union[float, Sequence[float], None] = None,
                            take_profit: Union[float, Sequence[float], None] = None,
                            trailing: Union[bool, Sequence[bool], None] = None,
                            guaranteed: Union[bool, Sequence[bool], None] = None,
                            legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame, list[dict]]:
        return self.modify_position(
            position=position,
            stop_loss=stop_loss,
            take_profit=take_profit,
            trailing=trailing,
            guaranteed=guaranteed,
            legacy=legacy)

    def modify_sell_position(self,
                             position: Union[int, Sequence[int]],
                             stop_loss: Union[float, Sequence[float], None] = None,
                             take_profit: Union[float, Sequence[float], None] = None,
                             trailing: Union[bool, Sequence[bool], None] = None,
                             guaranteed: Union[bool, Sequence[bool], None] = None,
                             legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame, list[dict]]:
        return self.modify_position(
            position=position,
            stop_loss=stop_loss,
            take_profit=take_profit,
            trailing=trailing,
            guaranteed=guaranteed,
            legacy=legacy)

    def close_position(self,
                       position: Union[int, Sequence[int], None] = None,
                       volume: Union[int, Sequence[int], None] = None,
                       legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame, list[dict]]:
        def _fetch_():
            pairs = self._resolve_positions_(position, volume)
            rows = [self._close_position_(position=i, volume=v) for i, v in pairs]
            if legacy is MISSING: return rows
            return self._api_.frame(rows, legacy=legacy)
        timer, result = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Close Position Operation: Closed {len(result)} positions ({timer.result()})")
        return result

    def close_buy_position(self,
                           position: Union[int, Sequence[int], None] = None,
                           volume: Union[int, Sequence[int], None] = None,
                           legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame, list[dict]]:
        return self.close_position(
            position=position,
            volume=volume,
            legacy=legacy)

    def close_sell_position(self,
                            position: Union[int, Sequence[int], None] = None,
                            volume: Union[int, Sequence[int], None] = None,
                            legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame, list[dict]]:
        return self.close_position(
            position=position,
            volume=volume,
            legacy=legacy)

    def _order_(self,
                order_type: Union[str, int],
                side: Union[str, int],
                symbol: int,
                volume: int,
                *,
                limit_price: Union[float, None] = None,
                stop_price: Union[float, None] = None,
                base_slippage_price: Union[float, None] = None,
                slippage_points: Union[int, None] = None,
                stop_loss: Union[float, None] = None,
                take_profit: Union[float, None] = None,
                time_in_force: Union[str, int, None] = None,
                expiration: Union[datetime, None] = None,
                label: Union[str, None] = None,
                comment: Union[str, None] = None,
                client_order_id: Union[str, None] = None,
                position_id: Union[int, None] = None,
                trailing: bool = False,
                guaranteed: bool = False) -> dict:
        from ctrader_open_api import Protobuf
        from Library.Spotware.Market import MarketAPI
        kwargs = {
            "ctidTraderAccountId": self._api_._account_id_,
            "symbolId": int(symbol),
            "orderType": self._order_type_(order_type),
            "tradeSide": self._side_(side),
            "volume": int(volume)
        }
        if limit_price is not None: kwargs["limitPrice"] = float(limit_price)
        if stop_price is not None: kwargs["stopPrice"] = float(stop_price)
        if base_slippage_price is not None: kwargs["baseSlippagePrice"] = float(base_slippage_price)
        if slippage_points is not None: kwargs["slippageInPoints"] = int(slippage_points)
        if stop_loss is not None: kwargs["stopLoss"] = float(stop_loss)
        if take_profit is not None: kwargs["takeProfit"] = float(take_profit)
        tif = self._tif_(time_in_force)
        if tif is not None: kwargs["timeInForce"] = tif
        if expiration is not None: kwargs["expirationTimestamp"] = MarketAPI._millis_(expiration)
        if label is not None: kwargs["label"] = str(label)
        if comment is not None: kwargs["comment"] = str(comment)
        if client_order_id is not None: kwargs["clientOrderId"] = str(client_order_id)
        if position_id is not None: kwargs["positionId"] = int(position_id)
        if trailing: kwargs["trailingStopLoss"] = True
        if guaranteed: kwargs["guaranteedStopLoss"] = True
        request = Protobuf.get("ProtoOANewOrderReq", **kwargs)
        response = self._api_._send_(request)
        return self._execution_(payload=response)

    def _modify_order_(self,
                       order: int,
                       volume: Union[int, None] = None,
                       limit_price: Union[float, None] = None,
                       stop_price: Union[float, None] = None,
                       stop_loss: Union[float, None] = None,
                       take_profit: Union[float, None] = None,
                       expiration: Union[datetime, None] = None,
                       slippage_points: Union[int, None] = None,
                       trailing: Union[bool, None] = None,
                       guaranteed: Union[bool, None] = None) -> dict:
        from ctrader_open_api import Protobuf
        from Library.Spotware.Market import MarketAPI
        kwargs = {
            "ctidTraderAccountId": self._api_._account_id_,
            "orderId": int(order)
        }
        if volume is not None: kwargs["volume"] = int(volume)
        if limit_price is not None: kwargs["limitPrice"] = float(limit_price)
        if stop_price is not None: kwargs["stopPrice"] = float(stop_price)
        if stop_loss is not None: kwargs["stopLoss"] = float(stop_loss)
        if take_profit is not None: kwargs["takeProfit"] = float(take_profit)
        if expiration is not None: kwargs["expirationTimestamp"] = MarketAPI._millis_(expiration)
        if slippage_points is not None: kwargs["slippageInPoints"] = int(slippage_points)
        if trailing is not None: kwargs["trailingStopLoss"] = bool(trailing)
        if guaranteed is not None: kwargs["guaranteedStopLoss"] = bool(guaranteed)
        request = Protobuf.get("ProtoOAAmendOrderReq", **kwargs)
        response = self._api_._send_(request)
        return self._execution_(payload=response)

    def _modify_position_(self,
                          position: int,
                          stop_loss: Union[float, None] = None,
                          take_profit: Union[float, None] = None,
                          trailing: Union[bool, None] = None,
                          guaranteed: Union[bool, None] = None) -> dict:
        from ctrader_open_api import Protobuf
        kwargs = {
            "ctidTraderAccountId": self._api_._account_id_,
            "positionId": int(position)
        }
        if stop_loss is not None: kwargs["stopLoss"] = float(stop_loss)
        if take_profit is not None: kwargs["takeProfit"] = float(take_profit)
        if trailing is not None: kwargs["trailingStopLoss"] = bool(trailing)
        if guaranteed is not None: kwargs["guaranteedStopLoss"] = bool(guaranteed)
        request = Protobuf.get("ProtoOAAmendPositionSLTPReq", **kwargs)
        response = self._api_._send_(request)
        return self._execution_(payload=response)

    def _close_order_(self, order: int) -> dict:
        from ctrader_open_api import Protobuf
        request = Protobuf.get("ProtoOACancelOrderReq",
                               ctidTraderAccountId=self._api_._account_id_,
                               orderId=int(order))
        response = self._api_._send_(request)
        return self._execution_(payload=response)

    def _close_position_(self, position: int, volume: int) -> dict:
        from ctrader_open_api import Protobuf
        request = Protobuf.get("ProtoOAClosePositionReq",
                               ctidTraderAccountId=self._api_._account_id_,
                               positionId=int(position),
                               volume=int(volume))
        response = self._api_._send_(request)
        return self._execution_(payload=response)

    def _resolve_orders_(self, order: Union[int, Sequence[int], None]) -> list[int]:
        if order is None:
            orders = self._api_.portfolio.orders(legacy=False)
            return [o.OrderID for o in orders] if orders else []
        if self._is_seq_(order): return [int(i) for i in order]
        return [int(order)]

    def _resolve_positions_(self,
                            position: Union[int, Sequence[int], None],
                            volume: Union[int, Sequence[int], None]) -> list[tuple[int, int]]:
        if position is None:
            positions = self._api_.portfolio.positions(legacy=False)
            if not positions: return []
            return [(p.PositionID, p.Volume) for p in positions]
        ids = [int(i) for i in position] if self._is_seq_(position) else [int(position)]
        if volume is None:
            positions = self._api_.portfolio.positions(legacy=False)
            vol_map = {p.PositionID: p.Volume for p in positions}
            return [(i, int(vol_map[i])) for i in ids]
        if self._is_seq_(volume):
            if len(volume) != len(ids):
                raise ValueError(f"Mismatched batch lengths: position ({len(ids)}) vs volume ({len(volume)})")
            return [(i, int(v)) for i, v in zip(ids, volume)]
        return [(i, int(volume)) for i in ids]

    def _execution_(self, payload) -> dict:
        name = type(payload).__name__ if payload is not None else ""
        row = {
            "ResponseType": name,
            "ExecutionType": None,
            "OrderID": None,
            "PositionID": None,
            "DealID": None,
            "ErrorCode": None,
            "Description": None
        }
        if name == "ProtoOAExecutionEvent":
            row["ExecutionType"] = int(payload.executionType)
            if payload.HasField("order"): row["OrderID"] = payload.order.orderId
            if payload.HasField("position"): row["PositionID"] = payload.position.positionId
            if payload.HasField("deal"):
                row["DealID"] = payload.deal.dealId
                row["OrderID"] = row["OrderID"] or payload.deal.orderId
                row["PositionID"] = row["PositionID"] or payload.deal.positionId
            if payload.HasField("errorCode"): row["ErrorCode"] = payload.errorCode
        elif name == "ProtoOAOrderErrorEvent":
            row["ErrorCode"] = payload.errorCode
            if payload.HasField("orderId"): row["OrderID"] = payload.orderId
            if payload.HasField("positionId"): row["PositionID"] = payload.positionId
            if payload.HasField("description"): row["Description"] = payload.description
        return row