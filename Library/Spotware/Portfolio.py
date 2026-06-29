from typing import Union
from datetime import datetime, timezone

from Library.Database.Dataframe import pd, pl
from Library.Utility.Service import ServiceAPI
from Library.Utility.Typing import MISSING, Missing
from Library.Utility.Datetime import timestamp_to_datetime
from Library.Portfolio.Account import AccountAPI, AccountType, MarginMode
from Library.Portfolio.Order import OrderAPI, Direction, OrderType, OrderStatus, TimeInForce
from Library.Portfolio.Position import PositionAPI, PositionType
from Library.Portfolio.Trade import TradeAPI

class PortfolioAPI(ServiceAPI):

    _TRADE_TYPE_MAP_ = {1: Direction.Buy, 2: Direction.Sell}
    _ACCOUNT_TYPE_MAP_ = {0: AccountType.Hedged, 1: AccountType.Netted, 2: "SpreadBetting"}
    _MARGIN_MODE_MAP_ = {0: MarginMode.Max, 1: MarginMode.Sum, 2: MarginMode.Net}

    @classmethod
    def _dt_(cls, ms: Union[int, None]) -> Union[datetime, None]:
        if not ms: return None
        return timestamp_to_datetime(ms, milliseconds=True).replace(tzinfo=timezone.utc)

    def account(self, legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame, list[AccountAPI]]:
        from ctrader_open_api import Protobuf
        def _fetch_():
            request = Protobuf.get("ProtoOATraderReq",
                                   ctidTraderAccountId=self._api_._account_id_)
            response = self._api_._send_(request)
            t = response.trader
            money = 10 ** int(getattr(t, "moneyDigits", 2) or 2)
            acc = AccountAPI(
                UID=str(t.ctidTraderAccountId),
                AccountType=self._ACCOUNT_TYPE_MAP_.get(int(t.accountType), None),
                MarginMode=self._MARGIN_MODE_MAP_.get(int(t.totalMarginCalculationType), None),
                Balance=t.balance / money,
                Leverage=t.leverageInCents / 100.0,
                db=self._api_._db_ if hasattr(self._api_, "_db_") else None
            )
            if legacy is MISSING: return [acc]
            return self._api_.frame([acc], legacy=legacy)
        timer, result = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Account Operation: Fetched account info ({timer.result()})")
        return result

    def accounts(self, legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame, list[AccountAPI]]:
        from ctrader_open_api import Protobuf
        def _fetch_():
            request = Protobuf.get("ProtoOAGetAccountListByAccessTokenReq",
                                   accessToken=self._api_._access_token_)
            response = self._api_._send_(request)
            data = []
            for a in response.ctidTraderAccount:
                acc = AccountAPI(
                    UID=str(a.ctidTraderAccountId),
                    db=self._api_._db_ if hasattr(self._api_, "_db_") else None
                )
                data.append(acc)
            if legacy is MISSING: return data
            return self._api_.frame(data, legacy=legacy)
        timer, result = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Accounts Operation: Fetched {len(result)} accounts ({timer.result()})")
        return result

    def order(self,
              id: int,
              legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame, list[OrderAPI]]:
        from ctrader_open_api import Protobuf
        def _fetch_():
            request = Protobuf.get("ProtoOAOrderDetailsReq",
                                   ctidTraderAccountId=self._api_._account_id_,
                                   orderId=int(id))
            response = self._api_._send_(request)
            data = [self._order_(response.order)] if response.HasField("order") else []
            if legacy is MISSING: return data
            return self._api_.frame(data, legacy=legacy)
        timer, result = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Order Operation: Fetched order {id} ({timer.result()})")
        return result

    def orders(self,
               start: Union[datetime, None] = None,
               stop: Union[datetime, None] = None,
               legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame, list[OrderAPI]]:
        from ctrader_open_api import Protobuf
        def _fetch_():
            from Library.Spotware.Market import MarketAPI
            if start is not None:
                stop_ = stop or datetime.now(timezone.utc)
                request = Protobuf.get("ProtoOAOrderListReq",
                                       ctidTraderAccountId=self._api_._account_id_,
                                       fromTimestamp=MarketAPI._millis_(start),
                                       toTimestamp=MarketAPI._millis_(stop_))
            else:
                request = Protobuf.get("ProtoOAReconcileReq",
                                       ctidTraderAccountId=self._api_._account_id_)
            response = self._api_._send_(request)
            data = [self._order_(o) for o in response.order]
            if legacy is MISSING: return data
            return self._api_.frame(data, legacy=legacy)
        timer, result = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Orders Operation: Fetched {len(result)} orders ({timer.result()})")
        return result

    def position(self,
                 id: int,
                 legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame, list[PositionAPI]]:
        from ctrader_open_api import Protobuf
        def _fetch_():
            request = Protobuf.get("ProtoOAReconcileReq",
                                   ctidTraderAccountId=self._api_._account_id_)
            response = self._api_._send_(request)
            data = [self._position_(p) for p in response.position if p.positionId == int(id)]
            if legacy is MISSING: return data
            return self._api_.frame(data, legacy=legacy)
        timer, result = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Position Operation: Fetched position {id} ({timer.result()})")
        return result

    def positions(self, legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame, list[PositionAPI]]:
        from ctrader_open_api import Protobuf
        def _fetch_():
            request = Protobuf.get("ProtoOAReconcileReq",
                                   ctidTraderAccountId=self._api_._account_id_)
            response = self._api_._send_(request)
            data = [self._position_(p) for p in response.position]
            if legacy is MISSING: return data
            return self._api_.frame(data, legacy=legacy)
        timer, result = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Positions Operation: Fetched {len(result)} positions ({timer.result()})")
        return result

    def trade(self,
              id: int,
              start: datetime,
              stop: Union[datetime, None] = None,
              legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame, list[TradeAPI]]:
        from ctrader_open_api import Protobuf
        stop = stop or datetime.now(timezone.utc)
        def _fetch_():
            from Library.Spotware.Market import MarketAPI
            request = Protobuf.get("ProtoOADealListReq",
                                   ctidTraderAccountId=self._api_._account_id_,
                                   fromTimestamp=MarketAPI._millis_(start),
                                   toTimestamp=MarketAPI._millis_(stop))
            response = self._api_._send_(request)
            data = [self._trade_(d) for d in response.deal
                    if d.dealId == int(id) and d.HasField("closePositionDetail")]
            if legacy is MISSING: return data
            return self._api_.frame(data, legacy=legacy)
        timer, result = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Trade Operation: Fetched trade {id} ({timer.result()})")
        return result

    def trades(self,
               start: datetime,
               stop: Union[datetime, None] = None,
               rows: int = 1000,
               legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame, list[TradeAPI]]:
        from ctrader_open_api import Protobuf
        stop = stop or datetime.now(timezone.utc)
        def _fetch_():
            from Library.Spotware.Market import MarketAPI
            request = Protobuf.get("ProtoOADealListReq",
                                   ctidTraderAccountId=self._api_._account_id_,
                                   fromTimestamp=MarketAPI._millis_(start),
                                   toTimestamp=MarketAPI._millis_(stop),
                                   maxRows=int(rows))
            response = self._api_._send_(request)
            data = [self._trade_(d) for d in response.deal if d.HasField("closePositionDetail")]
            if legacy is MISSING: return data
            return self._api_.frame(data, legacy=legacy)
        timer, result = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Trades Operation: Fetched {len(result)} trades ({timer.result()})")
        return result

    def pnl(self, legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame, list[dict]]:
        from ctrader_open_api import Protobuf
        def _fetch_():
            request = Protobuf.get("ProtoOAGetPositionUnrealizedPnLReq",
                                   ctidTraderAccountId=self._api_._account_id_)
            response = self._api_._send_(request)
            money = 10 ** int(getattr(response, "moneyDigits", 2) or 2)
            data = [{
                "PositionID": p.positionId,
                "GrossPnL": p.grossUnrealizedPnL / money,
                "NetPnL": p.netUnrealizedPnL / money
            } for p in response.positionUnrealizedPnL]
            if legacy is MISSING: return data
            return self._api_.frame(data, legacy=legacy)
        timer, result = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"PnL Operation: Fetched {len(result)} unrealized PnL rows ({timer.result()})")
        return result

    def cashflow(self,
                 start: datetime,
                 stop: Union[datetime, None] = None,
                 legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame, list[dict]]:
        from ctrader_open_api import Protobuf
        stop = stop or datetime.now(timezone.utc)
        def _fetch_():
            from Library.Spotware.Market import MarketAPI
            request = Protobuf.get("ProtoOACashFlowHistoryListReq",
                                   ctidTraderAccountId=self._api_._account_id_,
                                   fromTimestamp=MarketAPI._millis_(start),
                                   toTimestamp=MarketAPI._millis_(stop))
            response = self._api_._send_(request)
            data = []
            for h in response.depositWithdraw:
                money = 10 ** int(getattr(h, "moneyDigits", 2) or 2)
                data.append({
                    "BalanceHistoryId": h.balanceHistoryId,
                    "OperationType": h.operationType,
                    "Balance": h.balance / money,
                    "Delta": h.delta / money,
                    "Equity": (h.equity / money) if h.HasField("equity") else None,
                    "BalanceVersion": h.balanceVersion if h.HasField("balanceVersion") else None,
                    "ChangeBalanceTimestamp": self._dt_(h.changeBalanceTimestamp),
                    "ExternalNote": h.externalNote if h.HasField("externalNote") else None,
                    "MoneyDigits": h.moneyDigits
                })
            if legacy is MISSING: return data
            return self._api_.frame(data, legacy=legacy)
        timer, result = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"CashFlow Operation: Fetched {len(result)} cash flow entries ({timer.result()})")
        return result

    def _order_(self, o) -> OrderAPI:
        t = o.tradeData
        return OrderAPI(
            OrderID=o.orderId,
            PositionID=o.positionId if o.HasField("positionId") else None,
            SecurityUID=t.symbolId,
            Direction=self._TRADE_TYPE_MAP_.get(int(t.tradeSide), None),
            Volume=t.volume,
            OrderType=o.orderType,
            OrderStatus=o.orderStatus,
            TimeInForce=o.timeInForce,
            ExecutionPrice=o.executionPrice if o.HasField("executionPrice") else None,
            ExecutedVolume=o.executedVolume,
            LimitPrice=o.limitPrice if o.HasField("limitPrice") else None,
            StopPrice=o.stopPrice if o.HasField("stopPrice") else None,
            StopLossPrice=o.stopLoss if o.HasField("stopLoss") else None,
            TakeProfitPrice=o.takeProfit if o.HasField("takeProfit") else None,
            RelativeStopLoss=o.relativeStopLoss if o.HasField("relativeStopLoss") else None,
            RelativeTakeProfit=o.relativeTakeProfit if o.HasField("relativeTakeProfit") else None,
            BaseSlippagePrice=o.baseSlippagePrice if o.HasField("baseSlippagePrice") else None,
            SlippageInPoints=o.slippageInPoints if o.HasField("slippageInPoints") else None,
            ClosingOrder=o.closingOrder,
            ClientOrderID=o.clientOrderId,
            IsStopOut=o.isStopOut,
            TrailingStopLoss=o.trailingStopLoss,
            StopTriggerMethod=o.stopTriggerMethod,
            EntryTimestamp=self._dt_(t.openTimestamp),
            ExpirationTimestamp=self._dt_(o.expirationTimestamp) if o.HasField("expirationTimestamp") else None,
            LastUpdateTimestamp=self._dt_(o.utcLastUpdateTimestamp),
            Label=t.label,
            Comment=t.comment,
            db=self._api_._db_ if hasattr(self._api_, "_db_") else None
        )

    def _position_(self, p) -> PositionAPI:
        t = p.tradeData
        money = 10 ** int(getattr(p, "moneyDigits", 2) or 2)
        return PositionAPI(
            PositionID=p.positionId,
            SecurityUID=t.symbolId,
            Direction=self._TRADE_TYPE_MAP_.get(int(t.tradeSide), None),
            Volume=t.volume,
            EntryTimestamp=self._dt_(t.openTimestamp),
            EntryPrice=p.price,
            StopLossPrice=p.stopLoss if p.HasField("stopLoss") else None,
            TakeProfitPrice=p.takeProfit if p.HasField("takeProfit") else None,
            SwapPnL=p.swap / money,
            CommissionPnL=p.commission / money,
            UsedMargin=p.usedMargin / money,
            db=self._api_._db_ if hasattr(self._api_, "_db_") else None
        )

    def _trade_(self, d) -> TradeAPI:
        close = d.closePositionDetail
        money = 10 ** int(getattr(d, "moneyDigits", 2) or 2)
        gross = close.grossProfit / money
        swap = close.swap / money
        commission = close.commission / money
        return TradeAPI(
            TradeID=d.dealId,
            PositionID=d.positionId,
            SecurityUID=d.symbolId,
            Direction=self._TRADE_TYPE_MAP_.get(int(d.tradeSide), None),
            Volume=close.closedVolume if close.HasField("closedVolume") else d.filledVolume,
            EntryPrice=close.entryPrice,
            ExitPrice=d.executionPrice if d.HasField("executionPrice") else None,
            ExitTimestamp=self._dt_(d.executionTimestamp),
            GrossPnL=gross,
            CommissionPnL=commission,
            SwapPnL=swap,
            NetPnL=gross + commission + swap,
            ExitBalance=close.balance / money,
            db=self._api_._db_ if hasattr(self._api_, "_db_") else None
        )