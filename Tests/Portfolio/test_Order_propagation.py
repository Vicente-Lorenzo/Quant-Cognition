import pytest
from Library.Portfolio.Order import OrderAPI
from Library.Universe.Security import SecurityAPI
from Library.Universe.Contract import ContractAPI

def test_order_security_propagates_contract():
    c1 = ContractAPI(PipSize=0.0001)
    s1 = SecurityAPI()
    s1.Contract = c1

    order = OrderAPI(ExecutionPrice=1.0500, LimitPrice=1.0400)
    assert order.ExecutionPrice.Contract is None
    assert order.LimitPrice.Contract is None

    order.Security = s1

    assert order.ExecutionPrice.Contract is c1
    assert order.LimitPrice.Contract is c1

def test_order_contract_propagates_contract():
    c1 = ContractAPI(PipSize=0.0001)

    order = OrderAPI(ExecutionPrice=1.0500, LimitPrice=1.0400)
    assert order.ExecutionPrice.Contract is None
    assert order.LimitPrice.Contract is None

    order.Contract = c1

    assert order.ExecutionPrice.Contract is c1
    assert order.LimitPrice.Contract is c1

def test_order_execution_price_propagates_reference():
    order = OrderAPI()
    order.LimitPrice = 1.0400

    assert order.LimitPrice.Reference == 1.0400

    order.ExecutionPrice = 1.0500
    assert order.LimitPrice.Reference == 1.0500

    order.StopLossPrice = 1.0300
    assert order.StopLossPrice.Reference == 1.0500