import pytest
from datetime import datetime, timezone

import Library.Market
import Library.Portfolio

from ctrader_open_api.messages.OpenApiMessages_pb2 import (
    ProtoOAExecutionEvent,
    ProtoOAOrderErrorEvent
)

def _execution(order_id: int | None = None, position_id: int | None = None, deal_id: int | None = None, exec_type: int = 2):
    ev = ProtoOAExecutionEvent()
    ev.ctidTraderAccountId = 123
    ev.executionType = exec_type
    if order_id is not None: ev.order.orderId = order_id
    if position_id is not None: ev.position.positionId = position_id
    if deal_id is not None:
        ev.deal.dealId = deal_id
        if order_id is not None: ev.deal.orderId = order_id
        if position_id is not None: ev.deal.positionId = position_id
    return ev

def test_market_order_buy_sends_correct_request(spotware):
    spotware._responses_.append(_execution(order_id=11, position_id=101, deal_id=201))
    df = spotware.execution.market_order("BUY", symbol=1, volume=1000)
    sent = spotware._sent_[0]
    assert type(sent).__name__ == "ProtoOANewOrderReq"
    assert sent.orderType == 1
    assert sent.tradeSide == 1
    assert sent.symbolId == 1
    assert sent.volume == 1000
    assert df["OrderID"][0] == 11
    assert df["PositionID"][0] == 101
    assert df["DealID"][0] == 201

def test_market_buy_order_delegates(spotware):
    spotware._responses_.append(_execution(order_id=12))
    spotware.execution.market_buy_order(symbol=2, volume=500)
    sent = spotware._sent_[0]
    assert sent.orderType == 1
    assert sent.tradeSide == 1
    assert sent.symbolId == 2
    assert sent.volume == 500

def test_market_sell_order_delegates(spotware):
    spotware._responses_.append(_execution(order_id=13))
    spotware.execution.market_sell_order(symbol=3, volume=750)
    sent = spotware._sent_[0]
    assert sent.orderType == 1
    assert sent.tradeSide == 2
    assert sent.symbolId == 3
    assert sent.volume == 750

def test_range_buy_order_sends_base_price_and_slippage(spotware):
    spotware._responses_.append(_execution(order_id=14))
    spotware.execution.range_buy_order(symbol=1, volume=1000, base_price=1.2345, slippage_points=5)
    sent = spotware._sent_[0]
    assert sent.orderType == 5
    assert sent.tradeSide == 1
    assert sent.baseSlippagePrice == pytest.approx(1.2345)
    assert sent.slippageInPoints == 5

def test_range_sell_order_sets_sell_side(spotware):
    spotware._responses_.append(_execution(order_id=15))
    spotware.execution.range_sell_order(symbol=1, volume=1000, base_price=1.2, slippage_points=3)
    sent = spotware._sent_[0]
    assert sent.orderType == 5
    assert sent.tradeSide == 2

def test_limit_buy_order_sends_limit_price_and_tif(spotware):
    spotware._responses_.append(_execution(order_id=21))
    spotware.execution.limit_buy_order(symbol=1, volume=1000, price=1.1, time_in_force="GTC")
    sent = spotware._sent_[0]
    assert sent.orderType == 2
    assert sent.tradeSide == 1
    assert sent.limitPrice == pytest.approx(1.1)
    assert sent.timeInForce == 2

def test_limit_sell_order_with_expiration(spotware):
    spotware._responses_.append(_execution(order_id=22))
    expiration = datetime(2030, 1, 1, tzinfo=timezone.utc)
    spotware.execution.limit_sell_order(symbol=1, volume=1000, price=1.2, time_in_force="GTD", expiration=expiration)
    sent = spotware._sent_[0]
    assert sent.orderType == 2
    assert sent.tradeSide == 2
    assert sent.limitPrice == pytest.approx(1.2)
    assert sent.timeInForce == 1
    assert sent.expirationTimestamp == 1893456000000

def test_stop_buy_order_sends_stop_price(spotware):
    spotware._responses_.append(_execution(order_id=31))
    spotware.execution.stop_buy_order(symbol=1, volume=1000, price=1.3, slippage_points=2)
    sent = spotware._sent_[0]
    assert sent.orderType == 3
    assert sent.tradeSide == 1
    assert sent.stopPrice == pytest.approx(1.3)
    assert sent.slippageInPoints == 2

def test_stop_sell_order_sets_sell_side(spotware):
    spotware._responses_.append(_execution(order_id=32))
    spotware.execution.stop_sell_order(symbol=1, volume=1000, price=1.1)
    sent = spotware._sent_[0]
    assert sent.orderType == 3
    assert sent.tradeSide == 2

def test_stop_limit_buy_order_sends_both_prices(spotware):
    spotware._responses_.append(_execution(order_id=41))
    spotware.execution.stop_limit_buy_order(symbol=1, volume=1000, stop_price=1.3, limit_price=1.31)
    sent = spotware._sent_[0]
    assert sent.orderType == 6
    assert sent.tradeSide == 1
    assert sent.stopPrice == pytest.approx(1.3)
    assert sent.limitPrice == pytest.approx(1.31)

def test_stop_limit_sell_order_sets_sell_side(spotware):
    spotware._responses_.append(_execution(order_id=42))
    spotware.execution.stop_limit_sell_order(symbol=1, volume=1000, stop_price=1.1, limit_price=1.09)
    sent = spotware._sent_[0]
    assert sent.orderType == 6
    assert sent.tradeSide == 2

def test_market_order_passes_sl_tp_and_flags(spotware):
    spotware._responses_.append(_execution(order_id=51))
    spotware.execution.market_order("BUY", symbol=1, volume=1000,
                                    stop_loss=1.0, take_profit=1.5,
                                    label="L", comment="C",
                                    client_order_id="CID",
                                    trailing=True, guaranteed=True)
    sent = spotware._sent_[0]
    assert sent.stopLoss == pytest.approx(1.0)
    assert sent.takeProfit == pytest.approx(1.5)
    assert sent.label == "L"
    assert sent.comment == "C"
    assert sent.clientOrderId == "CID"
    assert sent.trailingStopLoss is True
    assert sent.guaranteedStopLoss is True

def test_modify_order_sends_amend_request(spotware):
    spotware._responses_.append(_execution(order_id=61))
    spotware.execution.modify_order(order=61, volume=2000, limit_price=1.25,
                                    stop_loss=1.0, take_profit=1.5, trailing=True)
    sent = spotware._sent_[0]
    assert type(sent).__name__ == "ProtoOAAmendOrderReq"
    assert sent.orderId == 61
    assert sent.volume == 2000
    assert sent.limitPrice == pytest.approx(1.25)
    assert sent.stopLoss == pytest.approx(1.0)
    assert sent.takeProfit == pytest.approx(1.5)
    assert sent.trailingStopLoss is True

def test_modify_buy_order_delegates(spotware):
    spotware._responses_.append(_execution(order_id=62))
    spotware.execution.modify_buy_order(order=62, volume=1500)
    sent = spotware._sent_[0]
    assert type(sent).__name__ == "ProtoOAAmendOrderReq"
    assert sent.orderId == 62
    assert sent.volume == 1500

def test_modify_sell_order_delegates(spotware):
    spotware._responses_.append(_execution(order_id=63))
    spotware.execution.modify_sell_order(order=63, stop_price=1.15)
    sent = spotware._sent_[0]
    assert type(sent).__name__ == "ProtoOAAmendOrderReq"
    assert sent.orderId == 63
    assert sent.stopPrice == pytest.approx(1.15)

def test_close_order_sends_cancel_request(spotware):
    spotware._responses_.append(_execution(order_id=71))
    df = spotware.execution.close_order(order=71)
    sent = spotware._sent_[0]
    assert type(sent).__name__ == "ProtoOACancelOrderReq"
    assert sent.orderId == 71
    assert df["OrderID"][0] == 71

def test_close_buy_order_delegates(spotware):
    spotware._responses_.append(_execution(order_id=72))
    spotware.execution.close_buy_order(order=72)
    assert type(spotware._sent_[0]).__name__ == "ProtoOACancelOrderReq"
    assert spotware._sent_[0].orderId == 72

def test_close_sell_order_delegates(spotware):
    spotware._responses_.append(_execution(order_id=73))
    spotware.execution.close_sell_order(order=73)
    assert type(spotware._sent_[0]).__name__ == "ProtoOACancelOrderReq"
    assert spotware._sent_[0].orderId == 73

def test_modify_position_sends_amend_sltp_request(spotware):
    spotware._responses_.append(_execution(position_id=81))
    spotware.execution.modify_position(position=81, stop_loss=1.0, take_profit=1.5, trailing=True)
    sent = spotware._sent_[0]
    assert type(sent).__name__ == "ProtoOAAmendPositionSLTPReq"
    assert sent.positionId == 81
    assert sent.stopLoss == pytest.approx(1.0)
    assert sent.takeProfit == pytest.approx(1.5)
    assert sent.trailingStopLoss is True

def test_modify_buy_position_delegates(spotware):
    spotware._responses_.append(_execution(position_id=82))
    spotware.execution.modify_buy_position(position=82, stop_loss=1.0)
    assert type(spotware._sent_[0]).__name__ == "ProtoOAAmendPositionSLTPReq"
    assert spotware._sent_[0].positionId == 82

def test_modify_sell_position_delegates(spotware):
    spotware._responses_.append(_execution(position_id=83))
    spotware.execution.modify_sell_position(position=83, take_profit=1.5)
    assert type(spotware._sent_[0]).__name__ == "ProtoOAAmendPositionSLTPReq"
    assert spotware._sent_[0].positionId == 83

def test_close_position_sends_close_request(spotware):
    spotware._responses_.append(_execution(position_id=91, deal_id=301))
    df = spotware.execution.close_position(position=91, volume=1000)
    sent = spotware._sent_[0]
    assert type(sent).__name__ == "ProtoOAClosePositionReq"
    assert sent.positionId == 91
    assert sent.volume == 1000
    assert df["PositionID"][0] == 91
    assert df["DealID"][0] == 301

def test_close_buy_position_delegates(spotware):
    spotware._responses_.append(_execution(position_id=92))
    spotware.execution.close_buy_position(position=92, volume=500)
    sent = spotware._sent_[0]
    assert type(sent).__name__ == "ProtoOAClosePositionReq"
    assert sent.positionId == 92
    assert sent.volume == 500

def test_close_sell_position_delegates(spotware):
    spotware._responses_.append(_execution(position_id=93))
    spotware.execution.close_sell_position(position=93, volume=250)
    sent = spotware._sent_[0]
    assert type(sent).__name__ == "ProtoOAClosePositionReq"
    assert sent.positionId == 93
    assert sent.volume == 250

def test_execution_frame_captures_order_error(spotware):
    err = ProtoOAOrderErrorEvent()
    err.ctidTraderAccountId = 123
    err.errorCode = "MARKET_CLOSED"
    err.orderId = 99
    err.description = "Market is closed"
    spotware._responses_.append(err)
    df = spotware.execution.market_order("BUY", symbol=1, volume=1000)
    assert df["ResponseType"][0] == "ProtoOAOrderErrorEvent"
    assert df["ErrorCode"][0] == "MARKET_CLOSED"
    assert df["OrderID"][0] == 99
    assert df["Description"][0] == "Market is closed"
