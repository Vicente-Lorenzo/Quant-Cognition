import pytest
from Library.Market.Bar import BarAPI
from Library.Market.Tick import TickAPI
from Library.Universe.Security import SecurityAPI
from Library.Universe.Contract import ContractAPI

def test_bar_security_propagates_security():
    s1 = SecurityAPI(UID=999)
    
    t_gap = TickAPI(Ask=1.0)
    t_open = TickAPI(Ask=1.1)
    
    bar = BarAPI(GapTick=t_gap, OpenTick=t_open)
    assert bar.GapTick.Security is None
    assert bar.OpenTick.Security is None

    bar.Security = s1
    
    assert bar.GapTick.Security is s1
    assert bar.OpenTick.Security is s1
