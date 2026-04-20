import Library.Market
import Library.Portfolio

from ctrader_open_api.messages.OpenApiMessages_pb2 import (
    ProtoOASymbolsListRes,
    ProtoOASymbolByIdRes,
    ProtoOAAssetListRes,
    ProtoOAAssetClassListRes,
    ProtoOASymbolCategoryListRes
)

def _add_symbol(response, symbol_id, name, asset_base=10, asset_quote=20, category=5, archived=False):
    if archived:
        s = response.archivedSymbol.add()
        s.symbolId = symbol_id
        s.name = name
        s.description = f"{name} desc"
    else:
        s = response.symbol.add()
        s.symbolId = symbol_id
        s.symbolName = name
        s.enabled = True
        s.baseAssetId = asset_base
        s.quoteAssetId = asset_quote
        s.symbolCategoryId = category
        s.description = f"{name} desc"

def test_tickers_parses_light_symbols(spotware):
    res = ProtoOASymbolsListRes()
    res.ctidTraderAccountId = 123
    _add_symbol(res, 1, "EURUSD")
    _add_symbol(res, 2, "GBPUSD")
    spotware._responses_.append(res)
    df = spotware.universe.tickers()
    assert len(df) == 2
    assert df["SecurityUID"].to_list() == [1, 2]
    assert df["TickerUID"].to_list() == ["EURUSD", "GBPUSD"]
    sent = spotware._sent_[0]
    assert type(sent).__name__ == "ProtoOASymbolsListReq"
    assert sent.ctidTraderAccountId == 123
    assert sent.includeArchivedSymbols is False

def test_tickers_includes_archived_when_flag_set(spotware):
    res = ProtoOASymbolsListRes()
    res.ctidTraderAccountId = 123
    _add_symbol(res, 1, "ACTIVE")
    _add_symbol(res, 99, "OLD", archived=True)
    spotware._responses_.append(res)
    df = spotware.universe.tickers(archived=True)
    assert len(df) == 2
    assert set(df["SecurityUID"].to_list()) == {1, 99}
    assert spotware._sent_[0].includeArchivedSymbols is True

def test_tickers_empty_response(spotware):
    spotware._responses_.append(ProtoOASymbolsListRes())
    df = spotware.universe.tickers()
    assert len(df) == 0

def test_ticker_detail_fetch(spotware):
    res = ProtoOASymbolByIdRes()
    s = res.symbol.add()
    s.symbolId = 1
    s.digits = 5
    s.pipPosition = 4
    s.lotSize = 100000
    s.minVolume = 1000
    s.maxVolume = 1000000000
    s.stepVolume = 1000
    s.commission = 30
    s.commissionType = 1
    s.swapLong = -1
    s.swapShort = -2
    spotware._responses_.append(res)
    df = spotware.universe.ticker(ids=1)
    assert len(df) == 1
    assert df["SecurityUID"][0] == 1
    assert df["Digits"][0] == 5
    assert df["PipPosition"][0] == 4
    assert df["LotSize"][0] == 100000
    sent = spotware._sent_[0]
    assert list(sent.symbolId) == [1]

def test_ticker_detail_multiple_ids(spotware):
    res = ProtoOASymbolByIdRes()
    a = res.symbol.add()
    a.symbolId = 1; a.digits = 5; a.pipPosition = 4
    b = res.symbol.add()
    b.symbolId = 2; b.digits = 3; b.pipPosition = 2
    spotware._responses_.append(res)
    df = spotware.universe.ticker(ids=[1, 2])
    assert len(df) == 2
    assert list(spotware._sent_[0].symbolId) == [1, 2]

def test_assets(spotware):
    res = ProtoOAAssetListRes()
    a = res.asset.add(); a.assetId = 1; a.name = "USD"; a.displayName = "US Dollar"; a.digits = 2
    b = res.asset.add(); b.assetId = 2; b.name = "EUR"; b.displayName = "Euro"; b.digits = 2
    spotware._responses_.append(res)
    df = spotware.universe.assets()
    assert len(df) == 2
    assert df["Name"].to_list() == ["USD", "EUR"]
    assert df["AssetId"].to_list() == [1, 2]

def test_asset_classes(spotware):
    res = ProtoOAAssetClassListRes()
    c = res.assetClass.add(); c.id = 1; c.name = "Forex"
    d = res.assetClass.add(); d.id = 2; d.name = "Metals"
    spotware._responses_.append(res)
    df = spotware.universe.classes()
    assert len(df) == 2
    assert df["AssetClassId"].to_list() == [1, 2]
    assert df["Name"].to_list() == ["Forex", "Metals"]

def test_categories(spotware):
    res = ProtoOASymbolCategoryListRes()
    c = res.symbolCategory.add(); c.id = 10; c.assetClassId = 1; c.name = "Major"
    d = res.symbolCategory.add(); d.id = 11; d.assetClassId = 1; d.name = "Minor"
    spotware._responses_.append(res)
    df = spotware.universe.categories()
    assert len(df) == 2
    assert df["CategoryId"].to_list() == [10, 11]
    assert df["AssetClassId"].to_list() == [1, 1]
    assert df["Name"].to_list() == ["Major", "Minor"]
