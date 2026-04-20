from datetime import datetime, timezone

from Library.Database.Dataframe import pd, pl
from Library.Utility.Service import ServiceAPI
from Library.Utility.Typing import MISSING, Missing
from Library.Spotware.Market import _millis_

_TRADE_TYPE_MAP_ = {1: "Buy", 2: "Sell"}
_ACCOUNT_TYPE_MAP_ = {0: "Hedged", 1: "Netted", 2: "SpreadBetting"}
_MARGIN_MODE_MAP_ = {0: "Max", 1: "Sum", 2: "Net"}

def _dt_(ms: int | None) -> datetime | None:
    if not ms: return None
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)

class PortfolioAPI(ServiceAPI):

    def account(self, legacy: bool | Missing = MISSING) -> pd.DataFrame | pl.DataFrame:
        from ctrader_open_api import Protobuf
        def _fetch_():
            request = Protobuf.get("ProtoOATraderReq",
                                   ctidTraderAccountId=self._api_._account_id_)
            response = self._api_._send_(request)
            t = response.trader
            money = 10 ** int(getattr(t, "moneyDigits", 2) or 2)
            data = [{
                "AccountID": t.ctidTraderAccountId,
                "TraderLogin": t.traderLogin,
                "BrokerName": t.brokerName,
                "DepositAssetId": t.depositAssetId,
                "AccountType": _ACCOUNT_TYPE_MAP_.get(int(t.accountType), str(t.accountType)),
                "MarginMode": _MARGIN_MODE_MAP_.get(int(t.totalMarginCalculationType), str(t.totalMarginCalculationType)),
                "Balance": t.balance / money,
                "BalanceVersion": t.balanceVersion,
                "ManagerBonus": t.managerBonus / money,
                "IbBonus": t.ibBonus / money,
                "NonWithdrawableBonus": t.nonWithdrawableBonus / money,
                "Leverage": t.leverageInCents / 100.0,
                "MaxLeverage": t.maxLeverage / 100.0,
                "AccessRights": t.accessRights,
                "SwapFree": t.swapFree,
                "FrenchRisk": t.frenchRisk,
                "IsLimitedRisk": t.isLimitedRisk,
                "LimitedRiskMarginCalculationStrategy": t.limitedRiskMarginCalculationStrategy,
                "RegistrationTimestamp": _dt_(t.registrationTimestamp),
                "MoneyDigits": t.moneyDigits
            }]
            return self._api_.frame(data, legacy=legacy)
        timer, df = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Account Operation: Fetched account info ({timer.result()})")
        return df

    def accounts(self, legacy: bool | Missing = MISSING) -> pd.DataFrame | pl.DataFrame:
        from ctrader_open_api import Protobuf
        def _fetch_():
            request = Protobuf.get("ProtoOAGetAccountListByAccessTokenReq",
                                   accessToken=self._api_._access_token_)
            response = self._api_._send_(request)
            data = [{
                "AccountID": a.ctidTraderAccountId,
                "TraderLogin": a.traderLogin,
                "IsLive": a.isLive,
                "LastClosingDealTimestamp": _dt_(a.lastClosingDealTimestamp),
                "LastBalanceUpdateTimestamp": _dt_(a.lastBalanceUpdateTimestamp)
            } for a in response.ctidTraderAccount]
            return self._api_.frame(data, legacy=legacy)
        timer, df = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Accounts Operation: Fetched {len(df)} accounts ({timer.result()})")
        return df

    def order(self,
              id: int,
              legacy: bool | Missing = MISSING) -> pd.DataFrame | pl.DataFrame:
        from ctrader_open_api import Protobuf
        def _fetch_():
            request = Protobuf.get("ProtoOAOrderDetailsReq",
                                   ctidTraderAccountId=self._api_._account_id_,
                                   orderId=int(id))
            response = self._api_._send_(request)
            data = [self._order_row_(response.order)] if response.HasField("order") else []
            return self._api_.frame(data, legacy=legacy)
        timer, df = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Order Operation: Fetched order {id} ({timer.result()})")
        return df

    def orders(self,
               start: datetime | None = None,
               stop: datetime | None = None,
               legacy: bool | Missing = MISSING) -> pd.DataFrame | pl.DataFrame:
        from ctrader_open_api import Protobuf
        def _fetch_():
            if start is not None:
                stop_ = stop or datetime.now(timezone.utc)
                request = Protobuf.get("ProtoOAOrderListReq",
                                       ctidTraderAccountId=self._api_._account_id_,
                                       fromTimestamp=_millis_(start),
                                       toTimestamp=_millis_(stop_))
            else:
                request = Protobuf.get("ProtoOAReconcileReq",
                                       ctidTraderAccountId=self._api_._account_id_)
            response = self._api_._send_(request)
            data = [self._order_row_(o) for o in response.order]
            return self._api_.frame(data, legacy=legacy)
        timer, df = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Orders Operation: Fetched {len(df)} orders ({timer.result()})")
        return df

    def position(self,
                 id: int,
                 legacy: bool | Missing = MISSING) -> pd.DataFrame | pl.DataFrame:
        from ctrader_open_api import Protobuf
        def _fetch_():
            request = Protobuf.get("ProtoOAReconcileReq",
                                   ctidTraderAccountId=self._api_._account_id_)
            response = self._api_._send_(request)
            data = [self._position_row_(p) for p in response.position if p.positionId == int(id)]
            return self._api_.frame(data, legacy=legacy)
        timer, df = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Position Operation: Fetched position {id} ({timer.result()})")
        return df

    def positions(self, legacy: bool | Missing = MISSING) -> pd.DataFrame | pl.DataFrame:
        from ctrader_open_api import Protobuf
        def _fetch_():
            request = Protobuf.get("ProtoOAReconcileReq",
                                   ctidTraderAccountId=self._api_._account_id_)
            response = self._api_._send_(request)
            data = [self._position_row_(p) for p in response.position]
            return self._api_.frame(data, legacy=legacy)
        timer, df = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Positions Operation: Fetched {len(df)} positions ({timer.result()})")
        return df

    def trade(self,
              id: int,
              start: datetime,
              stop: datetime | None = None,
              legacy: bool | Missing = MISSING) -> pd.DataFrame | pl.DataFrame:
        from ctrader_open_api import Protobuf
        stop = stop or datetime.now(timezone.utc)
        def _fetch_():
            request = Protobuf.get("ProtoOADealListReq",
                                   ctidTraderAccountId=self._api_._account_id_,
                                   fromTimestamp=_millis_(start),
                                   toTimestamp=_millis_(stop))
            response = self._api_._send_(request)
            data = [self._trade_row_(d) for d in response.deal
                    if d.dealId == int(id) and d.HasField("closePositionDetail")]
            return self._api_.frame(data, legacy=legacy)
        timer, df = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Trade Operation: Fetched trade {id} ({timer.result()})")
        return df

    def trades(self,
               start: datetime,
               stop: datetime | None = None,
               rows: int = 1000,
               legacy: bool | Missing = MISSING) -> pd.DataFrame | pl.DataFrame:
        from ctrader_open_api import Protobuf
        stop = stop or datetime.now(timezone.utc)
        def _fetch_():
            request = Protobuf.get("ProtoOADealListReq",
                                   ctidTraderAccountId=self._api_._account_id_,
                                   fromTimestamp=_millis_(start),
                                   toTimestamp=_millis_(stop),
                                   maxRows=int(rows))
            response = self._api_._send_(request)
            data = [self._trade_row_(d) for d in response.deal if d.HasField("closePositionDetail")]
            return self._api_.frame(data, legacy=legacy)
        timer, df = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Trades Operation: Fetched {len(df)} trades ({timer.result()})")
        return df

    def pnl(self, legacy: bool | Missing = MISSING) -> pd.DataFrame | pl.DataFrame:
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
            return self._api_.frame(data, legacy=legacy)
        timer, df = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"PnL Operation: Fetched {len(df)} unrealized PnL rows ({timer.result()})")
        return df

    def cashflow(self,
                 start: datetime,
                 stop: datetime | None = None,
                 legacy: bool | Missing = MISSING) -> pd.DataFrame | pl.DataFrame:
        from ctrader_open_api import Protobuf
        stop = stop or datetime.now(timezone.utc)
        def _fetch_():
            request = Protobuf.get("ProtoOACashFlowHistoryListReq",
                                   ctidTraderAccountId=self._api_._account_id_,
                                   fromTimestamp=_millis_(start),
                                   toTimestamp=_millis_(stop))
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
                    "ChangeBalanceTimestamp": _dt_(h.changeBalanceTimestamp),
                    "ExternalNote": h.externalNote if h.HasField("externalNote") else None,
                    "MoneyDigits": h.moneyDigits
                })
            return self._api_.frame(data, legacy=legacy)
        timer, df = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"CashFlow Operation: Fetched {len(df)} cash flow entries ({timer.result()})")
        return df

    @staticmethod
    def _order_row_(o) -> dict:
        t = o.tradeData
        return {
            "OrderID": o.orderId,
            "PositionID": o.positionId if o.HasField("positionId") else None,
            "SecurityUID": t.symbolId,
            "TradeType": _TRADE_TYPE_MAP_.get(int(t.tradeSide), str(t.tradeSide)),
            "Volume": t.volume,
            "OrderType": o.orderType,
            "OrderStatus": o.orderStatus,
            "TimeInForce": o.timeInForce,
            "ExecutionPrice": o.executionPrice if o.HasField("executionPrice") else None,
            "ExecutedVolume": o.executedVolume,
            "LimitPrice": o.limitPrice if o.HasField("limitPrice") else None,
            "StopPrice": o.stopPrice if o.HasField("stopPrice") else None,
            "StopLossPrice": o.stopLoss if o.HasField("stopLoss") else None,
            "TakeProfitPrice": o.takeProfit if o.HasField("takeProfit") else None,
            "RelativeStopLoss": o.relativeStopLoss if o.HasField("relativeStopLoss") else None,
            "RelativeTakeProfit": o.relativeTakeProfit if o.HasField("relativeTakeProfit") else None,
            "BaseSlippagePrice": o.baseSlippagePrice if o.HasField("baseSlippagePrice") else None,
            "SlippageInPoints": o.slippageInPoints if o.HasField("slippageInPoints") else None,
            "ClosingOrder": o.closingOrder,
            "ClientOrderID": o.clientOrderId,
            "IsStopOut": o.isStopOut,
            "TrailingStopLoss": o.trailingStopLoss,
            "StopTriggerMethod": o.stopTriggerMethod,
            "EntryTimestamp": _dt_(t.openTimestamp),
            "ExpirationTimestamp": _dt_(o.expirationTimestamp) if o.HasField("expirationTimestamp") else None,
            "LastUpdateTimestamp": _dt_(o.utcLastUpdateTimestamp),
            "Label": t.label,
            "Comment": t.comment
        }

    @staticmethod
    def _position_row_(p) -> dict:
        t = p.tradeData
        money = 10 ** int(getattr(p, "moneyDigits", 2) or 2)
        return {
            "PositionID": p.positionId,
            "SecurityUID": t.symbolId,
            "TradeType": _TRADE_TYPE_MAP_.get(int(t.tradeSide), str(t.tradeSide)),
            "Volume": t.volume,
            "PositionStatus": p.positionStatus,
            "EntryTimestamp": _dt_(t.openTimestamp),
            "EntryPrice": p.price,
            "StopLossPrice": p.stopLoss if p.HasField("stopLoss") else None,
            "TakeProfitPrice": p.takeProfit if p.HasField("takeProfit") else None,
            "GuaranteedStopLoss": p.guaranteedStopLoss,
            "TrailingStopLoss": p.trailingStopLoss,
            "StopLossTriggerMethod": p.stopLossTriggerMethod,
            "SwapPnL": p.swap / money,
            "CommissionPnL": p.commission / money,
            "MirroringCommissionPnL": p.mirroringCommission / money,
            "UsedMargin": p.usedMargin / money,
            "MarginRate": p.marginRate,
            "Label": t.label,
            "Comment": t.comment,
            "LastUpdateTimestamp": _dt_(p.utcLastUpdateTimestamp),
            "MoneyDigits": p.moneyDigits
        }

    @staticmethod
    def _trade_row_(d) -> dict:
        close = d.closePositionDetail
        money = 10 ** int(getattr(d, "moneyDigits", 2) or 2)
        gross = close.grossProfit / money
        swap = close.swap / money
        commission = close.commission / money
        return {
            "TradeID": d.dealId,
            "PositionID": d.positionId,
            "OrderID": d.orderId,
            "SecurityUID": d.symbolId,
            "TradeType": _TRADE_TYPE_MAP_.get(int(d.tradeSide), str(d.tradeSide)),
            "Volume": close.closedVolume if close.HasField("closedVolume") else d.filledVolume,
            "EntryPrice": close.entryPrice,
            "ExitPrice": d.executionPrice if d.HasField("executionPrice") else None,
            "ExitTimestamp": _dt_(d.executionTimestamp),
            "GrossPnL": gross,
            "CommissionPnL": commission,
            "SwapPnL": swap,
            "NetPnL": gross + commission + swap,
            "PnLConversionFee": (close.pnlConversionFee / money) if close.HasField("pnlConversionFee") else None,
            "QuoteToDepositConversionRate": close.quoteToDepositConversionRate if close.HasField("quoteToDepositConversionRate") else None,
            "BaseToUsdConversionRate": d.baseToUsdConversionRate if d.HasField("baseToUsdConversionRate") else None,
            "ExitBalance": close.balance / money,
            "BalanceVersion": close.balanceVersion if close.HasField("balanceVersion") else None,
            "MarginRate": d.marginRate if d.HasField("marginRate") else None,
            "DealStatus": d.dealStatus,
            "LastUpdateTimestamp": _dt_(d.utcLastUpdateTimestamp),
            "MoneyDigits": d.moneyDigits
        }
