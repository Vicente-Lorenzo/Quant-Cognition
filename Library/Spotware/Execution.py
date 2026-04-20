from collections.abc import Sequence
from datetime import datetime

from Library.Database.Dataframe import pd, pl
from Library.Utility.Service import ServiceAPI
from Library.Utility.Typing import MISSING, Missing
from Library.Spotware.Market import _millis_

_SIDE_MAP_ = {"BUY": 1, "SELL": 2}
_ORDER_TYPE_MAP_ = {"MARKET": 1, "LIMIT": 2, "STOP": 3, "STOP_LOSS_TAKE_PROFIT": 4, "MARKET_RANGE": 5, "STOP_LIMIT": 6}
_TIME_IN_FORCE_MAP_ = {"GTD": 1, "GTC": 2, "IOC": 3, "FOK": 4, "MOO": 5,
                       "GOOD_TILL_DATE": 1, "GOOD_TILL_CANCEL": 2,
                       "IMMEDIATE_OR_CANCEL": 3, "FILL_OR_KILL": 4, "MARKET_ON_OPEN": 5}

def _side_(value: str | int) -> int:
    if isinstance(value, int): return value
    return _SIDE_MAP_[str(value).upper()]

def _order_type_(value: str | int) -> int:
    if isinstance(value, int): return value
    return _ORDER_TYPE_MAP_[str(value).upper()]

def _tif_(value: str | int | None) -> int | None:
    if value is None: return None
    if isinstance(value, int): return value
    return _TIME_IN_FORCE_MAP_[str(value).upper()]

def _is_seq_(value) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes))

def _broadcast_(**kwargs) -> list[dict]:
    lengths = {len(v) for v in kwargs.values() if _is_seq_(v)}
    if not lengths: return [kwargs]
    if len(lengths) > 1: raise ValueError(f"Mismatched batch lengths: {sorted(lengths)}")
    n = lengths.pop()
    return [{k: (v[i] if _is_seq_(v) else v) for k, v in kwargs.items()} for i in range(n)]

class ExecutionAPI(ServiceAPI):

    def market_order(self,
                     side: str | int | Sequence[str | int],
                     symbol: int | Sequence[int],
                     volume: int | Sequence[int],
                     stop_loss: float | Sequence[float] | None = None,
                     take_profit: float | Sequence[float] | None = None,
                     label: str | Sequence[str] | None = None,
                     comment: str | Sequence[str] | None = None,
                     client_order_id: str | Sequence[str] | None = None,
                     trailing: bool | Sequence[bool] = False,
                     guaranteed: bool | Sequence[bool] = False,
                     legacy: bool | Missing = MISSING) -> pd.DataFrame | pl.DataFrame:
        batches = _broadcast_(
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
            return self._api_.frame(rows, legacy=legacy)
        timer, df = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Market Order Operation: Placed {len(df)} orders ({timer.result()})")
        return df

    def market_buy_order(self,
                         symbol: int | Sequence[int],
                         volume: int | Sequence[int],
                         stop_loss: float | Sequence[float] | None = None,
                         take_profit: float | Sequence[float] | None = None,
                         label: str | Sequence[str] | None = None,
                         comment: str | Sequence[str] | None = None,
                         client_order_id: str | Sequence[str] | None = None,
                         trailing: bool | Sequence[bool] = False,
                         guaranteed: bool | Sequence[bool] = False,
                         legacy: bool | Missing = MISSING) -> pd.DataFrame | pl.DataFrame:
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
                          symbol: int | Sequence[int],
                          volume: int | Sequence[int],
                          stop_loss: float | Sequence[float] | None = None,
                          take_profit: float | Sequence[float] | None = None,
                          label: str | Sequence[str] | None = None,
                          comment: str | Sequence[str] | None = None,
                          client_order_id: str | Sequence[str] | None = None,
                          trailing: bool | Sequence[bool] = False,
                          guaranteed: bool | Sequence[bool] = False,
                          legacy: bool | Missing = MISSING) -> pd.DataFrame | pl.DataFrame:
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
                    side: str | int | Sequence[str | int],
                    symbol: int | Sequence[int],
                    volume: int | Sequence[int],
                    base_price: float | Sequence[float],
                    slippage_points: int | Sequence[int],
                    stop_loss: float | Sequence[float] | None = None,
                    take_profit: float | Sequence[float] | None = None,
                    label: str | Sequence[str] | None = None,
                    comment: str | Sequence[str] | None = None,
                    client_order_id: str | Sequence[str] | None = None,
                    trailing: bool | Sequence[bool] = False,
                    guaranteed: bool | Sequence[bool] = False,
                    legacy: bool | Missing = MISSING) -> pd.DataFrame | pl.DataFrame:
        batches = _broadcast_(
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
            return self._api_.frame(rows, legacy=legacy)
        timer, df = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Range Order Operation: Placed {len(df)} orders ({timer.result()})")
        return df

    def range_buy_order(self,
                        symbol: int | Sequence[int],
                        volume: int | Sequence[int],
                        base_price: float | Sequence[float],
                        slippage_points: int | Sequence[int],
                        stop_loss: float | Sequence[float] | None = None,
                        take_profit: float | Sequence[float] | None = None,
                        label: str | Sequence[str] | None = None,
                        comment: str | Sequence[str] | None = None,
                        client_order_id: str | Sequence[str] | None = None,
                        trailing: bool | Sequence[bool] = False,
                        guaranteed: bool | Sequence[bool] = False,
                        legacy: bool | Missing = MISSING) -> pd.DataFrame | pl.DataFrame:
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
                         symbol: int | Sequence[int],
                         volume: int | Sequence[int],
                         base_price: float | Sequence[float],
                         slippage_points: int | Sequence[int],
                         stop_loss: float | Sequence[float] | None = None,
                         take_profit: float | Sequence[float] | None = None,
                         label: str | Sequence[str] | None = None,
                         comment: str | Sequence[str] | None = None,
                         client_order_id: str | Sequence[str] | None = None,
                         trailing: bool | Sequence[bool] = False,
                         guaranteed: bool | Sequence[bool] = False,
                         legacy: bool | Missing = MISSING) -> pd.DataFrame | pl.DataFrame:
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
                    side: str | int | Sequence[str | int],
                    symbol: int | Sequence[int],
                    volume: int | Sequence[int],
                    price: float | Sequence[float],
                    stop_loss: float | Sequence[float] | None = None,
                    take_profit: float | Sequence[float] | None = None,
                    time_in_force: str | int | Sequence[str | int] | None = "GTC",
                    expiration: datetime | Sequence[datetime] | None = None,
                    label: str | Sequence[str] | None = None,
                    comment: str | Sequence[str] | None = None,
                    client_order_id: str | Sequence[str] | None = None,
                    trailing: bool | Sequence[bool] = False,
                    guaranteed: bool | Sequence[bool] = False,
                    legacy: bool | Missing = MISSING) -> pd.DataFrame | pl.DataFrame:
        batches = _broadcast_(
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
            return self._api_.frame(rows, legacy=legacy)
        timer, df = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Limit Order Operation: Placed {len(df)} orders ({timer.result()})")
        return df

    def limit_buy_order(self,
                        symbol: int | Sequence[int],
                        volume: int | Sequence[int],
                        price: float | Sequence[float],
                        stop_loss: float | Sequence[float] | None = None,
                        take_profit: float | Sequence[float] | None = None,
                        time_in_force: str | int | Sequence[str | int] | None = "GTC",
                        expiration: datetime | Sequence[datetime] | None = None,
                        label: str | Sequence[str] | None = None,
                        comment: str | Sequence[str] | None = None,
                        client_order_id: str | Sequence[str] | None = None,
                        trailing: bool | Sequence[bool] = False,
                        guaranteed: bool | Sequence[bool] = False,
                        legacy: bool | Missing = MISSING) -> pd.DataFrame | pl.DataFrame:
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
                         symbol: int | Sequence[int],
                         volume: int | Sequence[int],
                         price: float | Sequence[float],
                         stop_loss: float | Sequence[float] | None = None,
                         take_profit: float | Sequence[float] | None = None,
                         time_in_force: str | int | Sequence[str | int] | None = "GTC",
                         expiration: datetime | Sequence[datetime] | None = None,
                         label: str | Sequence[str] | None = None,
                         comment: str | Sequence[str] | None = None,
                         client_order_id: str | Sequence[str] | None = None,
                         trailing: bool | Sequence[bool] = False,
                         guaranteed: bool | Sequence[bool] = False,
                         legacy: bool | Missing = MISSING) -> pd.DataFrame | pl.DataFrame:
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
                   side: str | int | Sequence[str | int],
                   symbol: int | Sequence[int],
                   volume: int | Sequence[int],
                   price: float | Sequence[float],
                   stop_loss: float | Sequence[float] | None = None,
                   take_profit: float | Sequence[float] | None = None,
                   time_in_force: str | int | Sequence[str | int] | None = "GTC",
                   expiration: datetime | Sequence[datetime] | None = None,
                   slippage_points: int | Sequence[int] | None = None,
                   label: str | Sequence[str] | None = None,
                   comment: str | Sequence[str] | None = None,
                   client_order_id: str | Sequence[str] | None = None,
                   trailing: bool | Sequence[bool] = False,
                   guaranteed: bool | Sequence[bool] = False,
                   legacy: bool | Missing = MISSING) -> pd.DataFrame | pl.DataFrame:
        batches = _broadcast_(
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
            return self._api_.frame(rows, legacy=legacy)
        timer, df = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Stop Order Operation: Placed {len(df)} orders ({timer.result()})")
        return df

    def stop_buy_order(self,
                       symbol: int | Sequence[int],
                       volume: int | Sequence[int],
                       price: float | Sequence[float],
                       stop_loss: float | Sequence[float] | None = None,
                       take_profit: float | Sequence[float] | None = None,
                       time_in_force: str | int | Sequence[str | int] | None = "GTC",
                       expiration: datetime | Sequence[datetime] | None = None,
                       slippage_points: int | Sequence[int] | None = None,
                       label: str | Sequence[str] | None = None,
                       comment: str | Sequence[str] | None = None,
                       client_order_id: str | Sequence[str] | None = None,
                       trailing: bool | Sequence[bool] = False,
                       guaranteed: bool | Sequence[bool] = False,
                       legacy: bool | Missing = MISSING) -> pd.DataFrame | pl.DataFrame:
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
                        symbol: int | Sequence[int],
                        volume: int | Sequence[int],
                        price: float | Sequence[float],
                        stop_loss: float | Sequence[float] | None = None,
                        take_profit: float | Sequence[float] | None = None,
                        time_in_force: str | int | Sequence[str | int] | None = "GTC",
                        expiration: datetime | Sequence[datetime] | None = None,
                        slippage_points: int | Sequence[int] | None = None,
                        label: str | Sequence[str] | None = None,
                        comment: str | Sequence[str] | None = None,
                        client_order_id: str | Sequence[str] | None = None,
                        trailing: bool | Sequence[bool] = False,
                        guaranteed: bool | Sequence[bool] = False,
                        legacy: bool | Missing = MISSING) -> pd.DataFrame | pl.DataFrame:
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
                         side: str | int | Sequence[str | int],
                         symbol: int | Sequence[int],
                         volume: int | Sequence[int],
                         stop_price: float | Sequence[float],
                         limit_price: float | Sequence[float],
                         stop_loss: float | Sequence[float] | None = None,
                         take_profit: float | Sequence[float] | None = None,
                         time_in_force: str | int | Sequence[str | int] | None = "GTC",
                         expiration: datetime | Sequence[datetime] | None = None,
                         label: str | Sequence[str] | None = None,
                         comment: str | Sequence[str] | None = None,
                         client_order_id: str | Sequence[str] | None = None,
                         trailing: bool | Sequence[bool] = False,
                         guaranteed: bool | Sequence[bool] = False,
                         legacy: bool | Missing = MISSING) -> pd.DataFrame | pl.DataFrame:
        batches = _broadcast_(
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
            return self._api_.frame(rows, legacy=legacy)
        timer, df = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Stop Limit Order Operation: Placed {len(df)} orders ({timer.result()})")
        return df

    def stop_limit_buy_order(self,
                             symbol: int | Sequence[int],
                             volume: int | Sequence[int],
                             stop_price: float | Sequence[float],
                             limit_price: float | Sequence[float],
                             stop_loss: float | Sequence[float] | None = None,
                             take_profit: float | Sequence[float] | None = None,
                             time_in_force: str | int | Sequence[str | int] | None = "GTC",
                             expiration: datetime | Sequence[datetime] | None = None,
                             label: str | Sequence[str] | None = None,
                             comment: str | Sequence[str] | None = None,
                             client_order_id: str | Sequence[str] | None = None,
                             trailing: bool | Sequence[bool] = False,
                             guaranteed: bool | Sequence[bool] = False,
                             legacy: bool | Missing = MISSING) -> pd.DataFrame | pl.DataFrame:
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
                              symbol: int | Sequence[int],
                              volume: int | Sequence[int],
                              stop_price: float | Sequence[float],
                              limit_price: float | Sequence[float],
                              stop_loss: float | Sequence[float] | None = None,
                              take_profit: float | Sequence[float] | None = None,
                              time_in_force: str | int | Sequence[str | int] | None = "GTC",
                              expiration: datetime | Sequence[datetime] | None = None,
                              label: str | Sequence[str] | None = None,
                              comment: str | Sequence[str] | None = None,
                              client_order_id: str | Sequence[str] | None = None,
                              trailing: bool | Sequence[bool] = False,
                              guaranteed: bool | Sequence[bool] = False,
                              legacy: bool | Missing = MISSING) -> pd.DataFrame | pl.DataFrame:
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
                     order: int | Sequence[int],
                     volume: int | Sequence[int] | None = None,
                     limit_price: float | Sequence[float] | None = None,
                     stop_price: float | Sequence[float] | None = None,
                     stop_loss: float | Sequence[float] | None = None,
                     take_profit: float | Sequence[float] | None = None,
                     expiration: datetime | Sequence[datetime] | None = None,
                     slippage_points: int | Sequence[int] | None = None,
                     trailing: bool | Sequence[bool] | None = None,
                     guaranteed: bool | Sequence[bool] | None = None,
                     legacy: bool | Missing = MISSING) -> pd.DataFrame | pl.DataFrame:
        batches = _broadcast_(
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
            return self._api_.frame(rows, legacy=legacy)
        timer, df = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Modify Order Operation: Modified {len(df)} orders ({timer.result()})")
        return df

    def modify_buy_order(self,
                         order: int | Sequence[int],
                         volume: int | Sequence[int] | None = None,
                         limit_price: float | Sequence[float] | None = None,
                         stop_price: float | Sequence[float] | None = None,
                         stop_loss: float | Sequence[float] | None = None,
                         take_profit: float | Sequence[float] | None = None,
                         expiration: datetime | Sequence[datetime] | None = None,
                         slippage_points: int | Sequence[int] | None = None,
                         trailing: bool | Sequence[bool] | None = None,
                         guaranteed: bool | Sequence[bool] | None = None,
                         legacy: bool | Missing = MISSING) -> pd.DataFrame | pl.DataFrame:
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
                          order: int | Sequence[int],
                          volume: int | Sequence[int] | None = None,
                          limit_price: float | Sequence[float] | None = None,
                          stop_price: float | Sequence[float] | None = None,
                          stop_loss: float | Sequence[float] | None = None,
                          take_profit: float | Sequence[float] | None = None,
                          expiration: datetime | Sequence[datetime] | None = None,
                          slippage_points: int | Sequence[int] | None = None,
                          trailing: bool | Sequence[bool] | None = None,
                          guaranteed: bool | Sequence[bool] | None = None,
                          legacy: bool | Missing = MISSING) -> pd.DataFrame | pl.DataFrame:
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
                    order: int | Sequence[int] | None = None,
                    legacy: bool | Missing = MISSING) -> pd.DataFrame | pl.DataFrame:
        def _fetch_():
            ids = self._resolve_orders_(order)
            rows = [self._close_order_(order=i) for i in ids]
            return self._api_.frame(rows, legacy=legacy)
        timer, df = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Close Order Operation: Cancelled {len(df)} orders ({timer.result()})")
        return df

    def close_buy_order(self,
                        order: int | Sequence[int] | None = None,
                        legacy: bool | Missing = MISSING) -> pd.DataFrame | pl.DataFrame:
        return self.close_order(
            order=order,
            legacy=legacy)

    def close_sell_order(self,
                         order: int | Sequence[int] | None = None,
                         legacy: bool | Missing = MISSING) -> pd.DataFrame | pl.DataFrame:
        return self.close_order(
            order=order,
            legacy=legacy)

    def modify_position(self,
                        position: int | Sequence[int],
                        stop_loss: float | Sequence[float] | None = None,
                        take_profit: float | Sequence[float] | None = None,
                        trailing: bool | Sequence[bool] | None = None,
                        guaranteed: bool | Sequence[bool] | None = None,
                        legacy: bool | Missing = MISSING) -> pd.DataFrame | pl.DataFrame:
        batches = _broadcast_(
            position=position,
            stop_loss=stop_loss,
            take_profit=take_profit,
            trailing=trailing,
            guaranteed=guaranteed)
        def _fetch_():
            rows = [self._modify_position_(**p) for p in batches]
            return self._api_.frame(rows, legacy=legacy)
        timer, df = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Modify Position Operation: Modified {len(df)} positions ({timer.result()})")
        return df

    def modify_buy_position(self,
                            position: int | Sequence[int],
                            stop_loss: float | Sequence[float] | None = None,
                            take_profit: float | Sequence[float] | None = None,
                            trailing: bool | Sequence[bool] | None = None,
                            guaranteed: bool | Sequence[bool] | None = None,
                            legacy: bool | Missing = MISSING) -> pd.DataFrame | pl.DataFrame:
        return self.modify_position(
            position=position,
            stop_loss=stop_loss,
            take_profit=take_profit,
            trailing=trailing,
            guaranteed=guaranteed,
            legacy=legacy)

    def modify_sell_position(self,
                             position: int | Sequence[int],
                             stop_loss: float | Sequence[float] | None = None,
                             take_profit: float | Sequence[float] | None = None,
                             trailing: bool | Sequence[bool] | None = None,
                             guaranteed: bool | Sequence[bool] | None = None,
                             legacy: bool | Missing = MISSING) -> pd.DataFrame | pl.DataFrame:
        return self.modify_position(
            position=position,
            stop_loss=stop_loss,
            take_profit=take_profit,
            trailing=trailing,
            guaranteed=guaranteed,
            legacy=legacy)

    def close_position(self,
                       position: int | Sequence[int] | None = None,
                       volume: int | Sequence[int] | None = None,
                       legacy: bool | Missing = MISSING) -> pd.DataFrame | pl.DataFrame:
        def _fetch_():
            pairs = self._resolve_positions_(position, volume)
            rows = [self._close_position_(position=i, volume=v) for i, v in pairs]
            return self._api_.frame(rows, legacy=legacy)
        timer, df = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Close Position Operation: Closed {len(df)} positions ({timer.result()})")
        return df

    def close_buy_position(self,
                           position: int | Sequence[int] | None = None,
                           volume: int | Sequence[int] | None = None,
                           legacy: bool | Missing = MISSING) -> pd.DataFrame | pl.DataFrame:
        return self.close_position(
            position=position,
            volume=volume,
            legacy=legacy)

    def close_sell_position(self,
                            position: int | Sequence[int] | None = None,
                            volume: int | Sequence[int] | None = None,
                            legacy: bool | Missing = MISSING) -> pd.DataFrame | pl.DataFrame:
        return self.close_position(
            position=position,
            volume=volume,
            legacy=legacy)

    def _order_(self,
                order_type: str | int,
                side: str | int,
                symbol: int,
                volume: int,
                *,
                limit_price: float | None = None,
                stop_price: float | None = None,
                base_slippage_price: float | None = None,
                slippage_points: int | None = None,
                stop_loss: float | None = None,
                take_profit: float | None = None,
                time_in_force: str | int | None = None,
                expiration: datetime | None = None,
                label: str | None = None,
                comment: str | None = None,
                client_order_id: str | None = None,
                position_id: int | None = None,
                trailing: bool = False,
                guaranteed: bool = False) -> dict:
        from ctrader_open_api import Protobuf
        kwargs = {
            "ctidTraderAccountId": self._api_._account_id_,
            "symbolId": int(symbol),
            "orderType": _order_type_(order_type),
            "tradeSide": _side_(side),
            "volume": int(volume)
        }
        if limit_price is not None: kwargs["limitPrice"] = float(limit_price)
        if stop_price is not None: kwargs["stopPrice"] = float(stop_price)
        if base_slippage_price is not None: kwargs["baseSlippagePrice"] = float(base_slippage_price)
        if slippage_points is not None: kwargs["slippageInPoints"] = int(slippage_points)
        if stop_loss is not None: kwargs["stopLoss"] = float(stop_loss)
        if take_profit is not None: kwargs["takeProfit"] = float(take_profit)
        tif = _tif_(time_in_force)
        if tif is not None: kwargs["timeInForce"] = tif
        if expiration is not None: kwargs["expirationTimestamp"] = _millis_(expiration)
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
                       volume: int | None = None,
                       limit_price: float | None = None,
                       stop_price: float | None = None,
                       stop_loss: float | None = None,
                       take_profit: float | None = None,
                       expiration: datetime | None = None,
                       slippage_points: int | None = None,
                       trailing: bool | None = None,
                       guaranteed: bool | None = None) -> dict:
        from ctrader_open_api import Protobuf
        kwargs = {
            "ctidTraderAccountId": self._api_._account_id_,
            "orderId": int(order)
        }
        if volume is not None: kwargs["volume"] = int(volume)
        if limit_price is not None: kwargs["limitPrice"] = float(limit_price)
        if stop_price is not None: kwargs["stopPrice"] = float(stop_price)
        if stop_loss is not None: kwargs["stopLoss"] = float(stop_loss)
        if take_profit is not None: kwargs["takeProfit"] = float(take_profit)
        if expiration is not None: kwargs["expirationTimestamp"] = _millis_(expiration)
        if slippage_points is not None: kwargs["slippageInPoints"] = int(slippage_points)
        if trailing is not None: kwargs["trailingStopLoss"] = bool(trailing)
        if guaranteed is not None: kwargs["guaranteedStopLoss"] = bool(guaranteed)
        request = Protobuf.get("ProtoOAAmendOrderReq", **kwargs)
        response = self._api_._send_(request)
        return self._execution_(payload=response)

    def _modify_position_(self,
                          position: int,
                          stop_loss: float | None = None,
                          take_profit: float | None = None,
                          trailing: bool | None = None,
                          guaranteed: bool | None = None) -> dict:
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

    def _resolve_orders_(self, order: int | Sequence[int] | None) -> list[int]:
        if order is None:
            orders = self._api_.portfolio.orders()
            return orders["OrderID"].to_list() if len(orders) else []
        if _is_seq_(order): return [int(i) for i in order]
        return [int(order)]

    def _resolve_positions_(self,
                            position: int | Sequence[int] | None,
                            volume: int | Sequence[int] | None) -> list[tuple[int, int]]:
        if position is None:
            positions = self._api_.portfolio.positions()
            if not len(positions): return []
            return list(zip(positions["PositionID"].to_list(), positions["Volume"].to_list()))
        ids = [int(i) for i in position] if _is_seq_(position) else [int(position)]
        if volume is None:
            positions = self._api_.portfolio.positions()
            vol_map = dict(zip(positions["PositionID"].to_list(), positions["Volume"].to_list()))
            return [(i, int(vol_map[i])) for i in ids]
        if _is_seq_(volume):
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
