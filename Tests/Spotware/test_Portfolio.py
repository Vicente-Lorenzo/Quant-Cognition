import pytest
from datetime import datetime, timezone
import Library.Market
import Library.Portfolio
from ctrader_open_api.messages.OpenApiMessages_pb2 import (
    ProtoOAGetAccountListByAccessTokenRes,
    ProtoOATraderRes,
    ProtoOAReconcileRes,
    ProtoOAOrderListRes,
    ProtoOAOrderDetailsRes,
    ProtoOADealListRes,
    ProtoOAGetPositionUnrealizedPnLRes,
    ProtoOACashFlowHistoryListRes
)
def test_accounts_parses_response(spotware):
    res = ProtoOAGetAccountListByAccessTokenRes()
    res.accessToken = "tok"
    a = res.ctidTraderAccount.add(); a.ctidTraderAccountId = 1001; a.isLive = False; a.traderLogin = 9001
    b = res.ctidTraderAccount.add(); b.ctidTraderAccountId = 1002; b.isLive = True; b.traderLogin = 9002
    spotware._responses_.append(res)
    df = spotware.portfolio.accounts()
    assert len(df) == 2
    assert df["AccountID"].to_list() == [1001, 1002]
    assert df["IsLive"].to_list() == [False, True]
    assert type(spotware._sent_[0]).__name__ == "ProtoOAGetAccountListByAccessTokenReq"
    assert spotware._sent_[0].accessToken == "test_token"
def test_account_scales_balance_by_money_digits(spotware):
    res = ProtoOATraderRes()
    res.ctidTraderAccountId = 123
    t = res.trader
    t.ctidTraderAccountId = 123
    t.traderLogin = 9001
    t.brokerName = "Test Broker"
    t.depositAssetId = 1
    t.balance = 1000000
    t.balanceVersion = 1
    t.managerBonus = 0
    t.ibBonus = 0
    t.nonWithdrawableBonus = 0
    t.swapFree = False
    t.leverageInCents = 10000
    t.totalMarginCalculationType = 0
    t.maxLeverage = 30000
    t.frenchRisk = False
    t.registrationTimestamp = 0
    t.isLimitedRisk = False
    t.moneyDigits = 2
    spotware._responses_.append(res)
    df = spotware.portfolio.account()
    assert len(df) == 1
    assert df["AccountID"][0] == 123
    assert df["Balance"][0] == pytest.approx(10000.0)
    assert df["TraderLogin"][0] == 9001
    assert df["BrokerName"][0] == "Test Broker"
    assert df["AccountType"][0] == "Hedged"
    assert df["MarginMode"][0] == "Max"
    assert df["Leverage"][0] == pytest.approx(100.0)
    assert df["MoneyDigits"][0] == 2
def test_position_filters_by_id(spotware):
    res = ProtoOAReconcileRes()
    res.ctidTraderAccountId = 123
    p1 = res.position.add()
    p1.positionId = 111
    p1.tradeData.symbolId = 1
    p1.tradeData.volume = 1000
    p1.tradeData.tradeSide = 1
    p1.tradeData.openTimestamp = 1577836800000
    p1.tradeData.guaranteedStopLoss = False
    p1.positionStatus = 1
    p1.price = 1.0
    p1.swap = 0
    p1.commission = -100
    p1.marginRate = 1.0
    p1.mirroringCommission = 0
    p1.guaranteedStopLoss = False
    p1.usedMargin = 10000
    p1.utcLastUpdateTimestamp = 1577836800000
    p1.moneyDigits = 2
    p2 = res.position.add()
    p2.positionId = 222
    p2.tradeData.symbolId = 2
    p2.tradeData.volume = 2000
    p2.tradeData.tradeSide = 2
    p2.tradeData.openTimestamp = 1577836800000
    p2.tradeData.guaranteedStopLoss = False
    p2.positionStatus = 1
    p2.price = 1.2
    p2.swap = 0
    p2.commission = -200
    p2.marginRate = 1.0
    p2.mirroringCommission = 0
    p2.guaranteedStopLoss = False
    p2.usedMargin = 20000
    p2.utcLastUpdateTimestamp = 1577836800000
    p2.moneyDigits = 2
    spotware._responses_.append(res)
    df = spotware.portfolio.position(id=222)
    assert len(df) == 1
    assert df["PositionID"][0] == 222
    assert df["SecurityUID"][0] == 2
    assert df["Direction"][0] == "Sell"
    assert type(spotware._sent_[0]).__name__ == "ProtoOAReconcileReq"
def test_positions_parses_reconcile(spotware):
    res = ProtoOAReconcileRes()
    res.ctidTraderAccountId = 123
    p = res.position.add()
    p.positionId = 555
    p.tradeData.symbolId = 1
    p.tradeData.volume = 10000
    p.tradeData.tradeSide = 1
    p.tradeData.openTimestamp = 1577836800000
    p.tradeData.label = "L1"
    p.tradeData.comment = "c"
    p.tradeData.guaranteedStopLoss = False
    p.positionStatus = 1
    p.swap = 0
    p.price = 1.05
    p.commission = -200
    p.marginRate = 1.0
    p.mirroringCommission = 0
    p.guaranteedStopLoss = False
    p.usedMargin = 50000
    p.utcLastUpdateTimestamp = 1577836800000
    p.moneyDigits = 2
    spotware._responses_.append(res)
    df = spotware.portfolio.positions()
    assert len(df) == 1
    assert df["PositionID"][0] == 555
    assert df["SecurityUID"][0] == 1
    assert df["Direction"][0] == "Buy"
    assert df["Volume"][0] == 10000
    assert df["EntryPrice"][0] == pytest.approx(1.05)
    assert df["CommissionPnL"][0] == pytest.approx(-2.0)
    assert df["UsedMargin"][0] == pytest.approx(500.0)
def test_order_fetches_single_by_id(spotware):
    res = ProtoOAOrderDetailsRes()
    res.ctidTraderAccountId = 123
    o = res.order
    o.orderId = 42
    o.tradeData.symbolId = 3
    o.tradeData.volume = 2500
    o.tradeData.tradeSide = 1
    o.tradeData.openTimestamp = 1577836800000
    o.tradeData.guaranteedStopLoss = False
    o.orderType = 2
    o.orderStatus = 3
    o.executedVolume = 2500
    o.baseSlippagePrice = 0
    o.slippageInPoints = 0
    o.closingOrder = False
    o.timeInForce = 1
    spotware._responses_.append(res)
    df = spotware.portfolio.order(id=42)
    assert len(df) == 1
    assert df["OrderID"][0] == 42
    assert df["SecurityUID"][0] == 3
    assert df["Direction"][0] == "Buy"
    sent = spotware._sent_[0]
    assert type(sent).__name__ == "ProtoOAOrderDetailsReq"
    assert sent.orderId == 42
def test_orders_pending_via_reconcile(spotware):
    res = ProtoOAReconcileRes()
    res.ctidTraderAccountId = 123
    o = res.order.add()
    o.orderId = 1
    o.tradeData.symbolId = 5
    o.tradeData.volume = 1000
    o.tradeData.tradeSide = 2
    o.tradeData.openTimestamp = 1577836800000
    o.tradeData.guaranteedStopLoss = False
    o.orderType = 1
    o.orderStatus = 1
    o.executedVolume = 0
    o.baseSlippagePrice = 0
    o.slippageInPoints = 0
    o.closingOrder = False
    o.timeInForce = 1
    spotware._responses_.append(res)
    df = spotware.portfolio.orders()
    assert len(df) == 1
    assert df["OrderID"][0] == 1
    assert df["SecurityUID"][0] == 5
    assert df["Direction"][0] == "Sell"
    assert type(spotware._sent_[0]).__name__ == "ProtoOAReconcileReq"
def test_orders_historical_with_range(spotware):
    res = ProtoOAOrderListRes()
    res.ctidTraderAccountId = 123
    o = res.order.add()
    o.orderId = 2
    o.tradeData.symbolId = 7
    o.tradeData.volume = 5000
    o.tradeData.tradeSide = 1
    o.tradeData.openTimestamp = 1577836800000
    o.tradeData.guaranteedStopLoss = False
    o.orderType = 2
    o.orderStatus = 3
    o.executedVolume = 5000
    o.baseSlippagePrice = 0
    o.slippageInPoints = 0
    o.closingOrder = False
    o.timeInForce = 1
    res.hasMore = False
    spotware._responses_.append(res)
    df = spotware.portfolio.orders(
        start=datetime(2020, 1, 1, tzinfo=timezone.utc),
        stop=datetime(2020, 1, 2, tzinfo=timezone.utc)
    )
    assert len(df) == 1
    assert df["OrderID"][0] == 2
    assert df["Direction"][0] == "Buy"
    assert type(spotware._sent_[0]).__name__ == "ProtoOAOrderListReq"
    assert spotware._sent_[0].fromTimestamp == 1577836800000
def test_trade_filters_single_closing_deal_by_id(spotware):
    res = ProtoOADealListRes()
    res.ctidTraderAccountId = 123
    other = res.deal.add()
    other.dealId = 800
    other.orderId = 3
    other.positionId = 777
    other.volume = 500
    other.filledVolume = 500
    other.symbolId = 1
    other.createTimestamp = 1577836800000
    other.executionTimestamp = 1577836800000
    other.utcLastUpdateTimestamp = 1577836800000
    other.executionPrice = 1.1
    other.tradeSide = 1
    other.dealStatus = 2
    other.moneyDigits = 2
    oc = other.closePositionDetail
    oc.entryPrice = 1.09
    oc.grossProfit = 1000
    oc.swap = 0
    oc.commission = -100
    oc.balance = 100000
    oc.closedVolume = 500
    d = res.deal.add()
    d.dealId = 801
    d.orderId = 4
    d.positionId = 778
    d.volume = 1000
    d.filledVolume = 1000
    d.symbolId = 2
    d.createTimestamp = 1577923200000
    d.executionTimestamp = 1577923200000
    d.utcLastUpdateTimestamp = 1577923200000
    d.executionPrice = 1.21
    d.tradeSide = 2
    d.dealStatus = 2
    d.moneyDigits = 2
    dc = d.closePositionDetail
    dc.entryPrice = 1.20
    dc.grossProfit = 5000
    dc.swap = 0
    dc.commission = -150
    dc.balance = 110000
    dc.closedVolume = 1000
    res.hasMore = False
    spotware._responses_.append(res)
    df = spotware.portfolio.trade(
        id=801,
        start=datetime(2020, 1, 1, tzinfo=timezone.utc),
        stop=datetime(2020, 1, 3, tzinfo=timezone.utc)
    )
    assert len(df) == 1
    assert df["TradeID"][0] == 801
    assert df["PositionID"][0] == 778
    assert df["SecurityUID"][0] == 2
    assert df["Direction"][0] == "Sell"
    sent = spotware._sent_[0]
    assert type(sent).__name__ == "ProtoOADealListReq"
def test_trades_filters_to_closing_deals(spotware):
    res = ProtoOADealListRes()
    res.ctidTraderAccountId = 123
    opening = res.deal.add()
    opening.dealId = 699
    opening.orderId = 1
    opening.positionId = 555
    opening.volume = 1000
    opening.filledVolume = 1000
    opening.symbolId = 1
    opening.createTimestamp = 1577836800000
    opening.executionTimestamp = 1577836800000
    opening.utcLastUpdateTimestamp = 1577836800000
    opening.executionPrice = 1.04
    opening.tradeSide = 1
    opening.dealStatus = 2
    opening.moneyDigits = 2
    d = res.deal.add()
    d.dealId = 700
    d.orderId = 2
    d.positionId = 555
    d.volume = 1000
    d.filledVolume = 1000
    d.symbolId = 1
    d.createTimestamp = 1577923200000
    d.executionTimestamp = 1577923200500
    d.utcLastUpdateTimestamp = 1577923200500
    d.executionPrice = 1.05
    d.tradeSide = 2
    d.dealStatus = 2
    d.marginRate = 1.0
    d.commission = -300
    d.baseToUsdConversionRate = 1.0
    d.moneyDigits = 2
    close = d.closePositionDetail
    close.entryPrice = 1.04
    close.grossProfit = 10000
    close.swap = -50
    close.commission = -300
    close.balance = 1009650
    close.quoteToDepositConversionRate = 1.0
    close.closedVolume = 1000
    close.balanceVersion = 2
    res.hasMore = False
    spotware._responses_.append(res)
    df = spotware.portfolio.trades(
        start=datetime(2020, 1, 1, tzinfo=timezone.utc),
        stop=datetime(2020, 1, 2, tzinfo=timezone.utc)
    )
    assert len(df) == 1
    assert df["TradeID"][0] == 700
    assert df["PositionID"][0] == 555
    assert df["SecurityUID"][0] == 1
    assert df["Direction"][0] == "Sell"
    assert df["EntryPrice"][0] == pytest.approx(1.04)
    assert df["ExitPrice"][0] == pytest.approx(1.05)
    assert df["GrossPnL"][0] == pytest.approx(100.0)
    assert df["CommissionPnL"][0] == pytest.approx(-3.0)
    assert df["SwapPnL"][0] == pytest.approx(-0.5)
    assert df["NetPnL"][0] == pytest.approx(96.5)
    assert df["ExitBalance"][0] == pytest.approx(10096.5)
    sent = spotware._sent_[0]
    assert type(sent).__name__ == "ProtoOADealListReq"
    assert sent.maxRows == 1000
    assert sent.fromTimestamp == 1577836800000
def test_pnl_scales_by_money_digits(spotware):
    res = ProtoOAGetPositionUnrealizedPnLRes()
    res.ctidTraderAccountId = 123
    res.moneyDigits = 2
    p = res.positionUnrealizedPnL.add()
    p.positionId = 555
    p.grossUnrealizedPnL = 12500
    p.netUnrealizedPnL = 12300
    spotware._responses_.append(res)
    df = spotware.portfolio.pnl()
    assert len(df) == 1
    assert df["PositionID"][0] == 555
    assert df["GrossPnL"][0] == pytest.approx(125.0)
    assert df["NetPnL"][0] == pytest.approx(123.0)
def test_cashflow_parses_entries(spotware):
    res = ProtoOACashFlowHistoryListRes()
    res.ctidTraderAccountId = 123
    h = res.depositWithdraw.add()
    h.operationType = 1
    h.balanceHistoryId = 1
    h.balance = 100000
    h.delta = 50000
    h.changeBalanceTimestamp = 1577836800000
    h.moneyDigits = 2
    spotware._responses_.append(res)
    df = spotware.portfolio.cashflow(
        start=datetime(2020, 1, 1, tzinfo=timezone.utc),
        stop=datetime(2020, 1, 2, tzinfo=timezone.utc)
    )
    assert len(df) == 1
    assert df["Balance"][0] == pytest.approx(1000.0)
    assert df["Delta"][0] == pytest.approx(500.0)
    assert df["OperationType"][0] == 1
    assert type(spotware._sent_[0]).__name__ == "ProtoOACashFlowHistoryListReq"