from Library.Market.Bar import BarAPI
from Library.Market.Point import PointAPI
from Library.Market.Tick import TickAPI
from Library.Universe.Security import SecurityAPI

def test_bar_security_propagates_to_every_tick():
    s1 = SecurityAPI(UID=999)
    gap, ask, bid = TickAPI(Ask=1.0), TickAPI(Ask=1.1), TickAPI(Bid=1.05)
    bar = BarAPI(GapPoint=PointAPI(gap, gap), OpenPoint=PointAPI(ask, bid))
    assert gap.Security is None and ask.Security is None and bid.Security is None
    bar.Security = s1
    assert gap.Security is s1 and ask.Security is s1 and bid.Security is s1