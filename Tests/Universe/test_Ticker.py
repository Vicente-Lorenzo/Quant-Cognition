from Library.Universe.Universe import UniverseAPI
from Library.Universe.Ticker import TickerAPI
from Library.Universe.Category import CategoryAPI
from Library.Database.Datapoint import DatapointAPI

def test_ticker_normalize_prefix():
    assert TickerAPI.normalize("OANDA:EURUSD") == "EURUSD"
    assert TickerAPI.normalize("BINANCE:BTCUSD") == "BTCUSD"

def test_ticker_normalize_suffix():
    assert TickerAPI.normalize("EURUSD.m") == "EURUSD"
    assert TickerAPI.normalize("GBPUSD.pro") == "GBPUSD"
    assert TickerAPI.normalize("AUDUSD.raw") == "AUDUSD"
    assert TickerAPI.normalize("USDJPY.ecn") == "USDJPY"
    assert TickerAPI.normalize("NZDUSD.s") == "NZDUSD"
    assert TickerAPI.normalize("USDCAD.std") == "USDCAD"
    assert TickerAPI.normalize("USDCHF.i") == "USDCHF"
    assert TickerAPI.normalize("EURGBP.ins") == "EURGBP"
    assert TickerAPI.normalize("EURJPY.z") == "EURJPY"
    assert TickerAPI.normalize("EURAUD.v") == "EURAUD"
    assert TickerAPI.normalize("EURCAD.x") == "EURCAD"
    assert TickerAPI.normalize("EURNZD.plus") == "EURNZD"
    assert TickerAPI.normalize("GBPJPY+") == "GBPJPY"
    assert TickerAPI.normalize("GBPCHF-") == "GBPCHF"
    assert TickerAPI.normalize("UK100_sb") == "UK100"
    assert TickerAPI.normalize("US30.c") == "US30"
    assert TickerAPI.normalize("GER40.cfd") == "GER40"

def test_ticker_normalize_special():
    assert TickerAPI.normalize("AAPL#") == "AAPL"
    assert TickerAPI.normalize("US30..") == "US30"
    assert TickerAPI.normalize("BTCUSD+_") == "BTCUSD"

def test_ticker_normalize_combined():
    assert TickerAPI.normalize("FX:EURUSD.m#") == "EURUSD"

def test_ticker_initialization(db):
    db.migrate(schema=UniverseAPI.Schema, table=CategoryAPI.Table, structure=CategoryAPI(db=db).Structure)
    try:
        ticker = TickerAPI(UID="oanda:eurusd.m", db=db)
        assert ticker.UID == "EURUSD"
    except ValueError:
        pass