from typing import Union
from datetime import datetime
from ctrader_open_api.messages.OpenApiModelMessages_pb2 import ProtoOATradeSide

from Library.Database.Dataframe import pd, pl
from Library.Utility.Datetime import utc_now
from Library.Utility.Service import ServiceAPI
from Library.Utility.Typing import MISSING, Missing

class PortfolioAPI(ServiceAPI):

    def _order_(self, order) -> dict:
        api, trade = self._api_, order.tradeData
        return {
            "OrderID": order.orderId,
            "PositionID": api._optional_(order, "positionId"),
            "Symbol": trade.symbolId,
            "Direction": api._named_(trade, "tradeSide"),
            "Volume": api._units_(trade.volume),
            "OrderType": api._named_(order, "orderType"),
            "OrderStatus": api._named_(order, "orderStatus"),
            "TimeInForce": api._named_(order, "timeInForce"),
            "ExecutionPrice": api._optional_(order, "executionPrice"),
            "ExecutedVolume": api._optional_(order, "executedVolume", api._units_),
            "LimitPrice": api._optional_(order, "limitPrice"),
            "StopPrice": api._optional_(order, "stopPrice"),
            "StopLossPrice": api._optional_(order, "stopLoss"),
            "TakeProfitPrice": api._optional_(order, "takeProfit"),
            "RelativeStopLoss": api._optional_(order, "relativeStopLoss", api._price_),
            "RelativeTakeProfit": api._optional_(order, "relativeTakeProfit", api._price_),
            "BaseSlippagePrice": api._optional_(order, "baseSlippagePrice"),
            "SlippageInPoints": api._optional_(order, "slippageInPoints"),
            "ClosingOrder": order.closingOrder,
            "ClientOrderID": order.clientOrderId,
            "IsStopOut": order.isStopOut,
            "TrailingStopLoss": order.trailingStopLoss,
            "StopTriggerMethod": api._named_(order, "stopTriggerMethod"),
            "EntryTimestamp": api._stamp_(trade.openTimestamp),
            "ExpirationTimestamp": api._stamp_(order.expirationTimestamp),
            "LastUpdateTimestamp": api._stamp_(order.utcLastUpdateTimestamp),
            "Label": trade.label,
            "Comment": trade.comment
        }

    def _position_(self, position) -> dict:
        api, trade, money = self._api_, position.tradeData, self._api_._money_(position)
        return {
            "PositionID": position.positionId,
            "Symbol": trade.symbolId,
            "Direction": api._named_(trade, "tradeSide"),
            "Volume": api._units_(trade.volume),
            "EntryTimestamp": api._stamp_(trade.openTimestamp),
            "EntryPrice": api._optional_(position, "price"),
            "StopLossPrice": api._optional_(position, "stopLoss"),
            "TakeProfitPrice": api._optional_(position, "takeProfit"),
            "SwapPnL": position.swap / money,
            "CommissionPnL": position.commission / money,
            "UsedMargin": position.usedMargin / money
        }

    def _trade_(self, deal) -> dict:
        api, close, money = self._api_, deal.closePositionDetail, self._api_._money_(deal)
        gross, commission, swap = close.grossProfit / money, close.commission / money, close.swap / money
        return {
            "TradeID": deal.dealId,
            "PositionID": deal.positionId,
            "Symbol": deal.symbolId,
            "Direction": api._label_(ProtoOATradeSide.DESCRIPTOR, ProtoOATradeSide.SELL if deal.tradeSide == ProtoOATradeSide.BUY else ProtoOATradeSide.BUY),
            "Volume": api._units_(close.closedVolume if close.HasField("closedVolume") else deal.filledVolume),
            "EntryPrice": close.entryPrice,
            "ExitPrice": api._optional_(deal, "executionPrice"),
            "ExitTimestamp": api._stamp_(deal.executionTimestamp),
            "GrossPnL": gross,
            "CommissionPnL": commission,
            "SwapPnL": swap,
            "NetPnL": gross + commission + swap,
            "ExitBalance": close.balance / money
        }

    def _paged_(self, request: str, field: str, key: str, start: datetime, stop: Union[datetime, None], **fields) -> list:
        api = self._api_
        lower, upper, found = api._epoch_(start), api._epoch_(stop or utc_now()), {}
        while True:
            response = api._request_(request, fromTimestamp=lower, toTimestamp=upper, **fields)
            items, known = getattr(response, field), len(found)
            for item in items: found.setdefault(getattr(item, key), item)
            if not response.hasMore or not items: return list(found.values())
            upper = min(min(item.utcLastUpdateTimestamp for item in items), upper) - (0 if len(found) > known else 1)
            if upper < lower: return list(found.values())

    def _cashflow_(self, entry) -> dict:
        api, money = self._api_, self._api_._money_(entry)
        return {
            "BalanceHistoryId": entry.balanceHistoryId,
            "OperationType": api._named_(entry, "operationType"),
            "Balance": entry.balance / money,
            "Delta": entry.delta / money,
            "Equity": api._optional_(entry, "equity", lambda equity: equity / money),
            "BalanceVersion": api._optional_(entry, "balanceVersion"),
            "ChangeBalanceTimestamp": api._stamp_(entry.changeBalanceTimestamp),
            "ExternalNote": api._optional_(entry, "externalNote"),
            "MoneyDigits": api._digits_(entry)
        }

    def account(self, legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame]:
        def _fetch_():
            api = self._api_
            trader = api._request_("ProtoOATraderReq").trader
            row = {
                "AccountID": trader.ctidTraderAccountId,
                "AccountType": api._named_(trader, "accountType"),
                "MarginMode": api._named_(trader, "totalMarginCalculationType"),
                "Balance": trader.balance / api._money_(trader),
                "Leverage": api._units_(trader.leverageInCents),
                "BrokerName": api._optional_(trader, "brokerName"),
                "DepositAssetID": trader.depositAssetId,
                "TraderLogin": api._optional_(trader, "traderLogin"),
                "MoneyDigits": api._digits_(trader)
            }
            return api.frame([row], legacy=legacy)
        timer, result = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Account Operation: Fetched account info ({timer.result()})")
        return result

    def accounts(self, legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame]:
        def _fetch_():
            api = self._api_
            response = api._request_("ProtoOAGetAccountListByAccessTokenReq", accessToken=api._access_token_)
            rows = [{"AccountID": account.ctidTraderAccountId, "IsLive": account.isLive, "TraderLogin": api._optional_(account, "traderLogin")} for account in response.ctidTraderAccount]
            return api.frame(rows, legacy=legacy)
        timer, result = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Accounts Operation: Fetched {len(result)} accounts ({timer.result()})")
        return result

    def order(self,
              id: int,
              legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame]:
        def _fetch_():
            response = self._api_._request_("ProtoOAOrderDetailsReq", orderId=int(id))
            rows = [self._order_(response.order)] if response.HasField("order") else []
            return self._api_.frame(rows, legacy=legacy)
        timer, result = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Order Operation: Fetched order {id} ({timer.result()})")
        return result

    def orders(self,
               start: Union[datetime, None] = None,
               stop: Union[datetime, None] = None,
               legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame]:
        def _fetch_():
            api = self._api_
            if start is None: return api.frame([self._order_(order) for order in api._request_("ProtoOAReconcileReq").order], legacy=legacy)
            return api.frame([self._order_(order) for order in self._paged_("ProtoOAOrderListReq", "order", "orderId", start, stop)], legacy=legacy)
        timer, result = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Orders Operation: Fetched {len(result)} orders ({timer.result()})")
        return result

    def position(self,
                 id: int,
                 legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame]:
        def _fetch_():
            response = self._api_._request_("ProtoOAReconcileReq")
            return self._api_.frame([self._position_(position) for position in response.position if position.positionId == int(id)], legacy=legacy)
        timer, result = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Position Operation: Fetched position {id} ({timer.result()})")
        return result

    def positions(self, legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame]:
        def _fetch_():
            response = self._api_._request_("ProtoOAReconcileReq")
            return self._api_.frame([self._position_(position) for position in response.position], legacy=legacy)
        timer, result = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Positions Operation: Fetched {len(result)} positions ({timer.result()})")
        return result

    def trade(self,
              id: int,
              start: datetime,
              stop: Union[datetime, None] = None,
              legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame]:
        def _fetch_():
            deals = self._paged_("ProtoOADealListReq", "deal", "dealId", start, stop)
            return self._api_.frame([self._trade_(deal) for deal in deals if deal.dealId == int(id) and deal.HasField("closePositionDetail")], legacy=legacy)
        timer, result = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Trade Operation: Fetched trade {id} ({timer.result()})")
        return result

    def trades(self,
               start: datetime,
               stop: Union[datetime, None] = None,
               rows: int = 1000,
               legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame]:
        def _fetch_():
            deals = self._paged_("ProtoOADealListReq", "deal", "dealId", start, stop, maxRows=int(rows))
            return self._api_.frame([self._trade_(deal) for deal in deals if deal.HasField("closePositionDetail")], legacy=legacy)
        timer, result = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Trades Operation: Fetched {len(result)} trades ({timer.result()})")
        return result

    def pnl(self, legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame]:
        def _fetch_():
            response = self._api_._request_("ProtoOAGetPositionUnrealizedPnLReq")
            money = self._api_._money_(response)
            rows = [{"PositionID": position.positionId, "GrossPnL": position.grossUnrealizedPnL / money, "NetPnL": position.netUnrealizedPnL / money} for position in response.positionUnrealizedPnL]
            return self._api_.frame(rows, legacy=legacy)
        timer, result = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"PnL Operation: Fetched {len(result)} unrealized PnL rows ({timer.result()})")
        return result

    def cashflow(self,
                 start: datetime,
                 stop: Union[datetime, None] = None,
                 legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame]:
        def _fetch_():
            api = self._api_
            lower, upper = api._epoch_(start), api._epoch_(stop or utc_now())
            entries = {}
            for window in range(lower, upper, 604800000):
                response = api._request_("ProtoOACashFlowHistoryListReq", fromTimestamp=window, toTimestamp=min(window + 604800000, upper))
                entries.update({entry.balanceHistoryId: self._cashflow_(entry) for entry in response.depositWithdraw})
            return api.frame(list(entries.values()), legacy=legacy)
        timer, result = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"CashFlow Operation: Fetched {len(result)} cash flow entries ({timer.result()})")
        return result