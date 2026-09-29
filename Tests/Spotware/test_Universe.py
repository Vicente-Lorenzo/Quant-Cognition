import pytest

import Library.Market
import Library.Portfolio
from Library.Spotware.Messages import (
    ProtoOAAssetClassListRes,
    ProtoOAAssetListRes,
    ProtoOASymbolByIdRes,
    ProtoOASymbolCategoryListRes,
    ProtoOASymbolsListRes
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
    assert df["Symbol"].to_list() == [1, 2]
    assert df["Ticker"].to_list() == ["EURUSD", "GBPUSD"]
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
    assert set(df["Symbol"].to_list()) == {1, 99}
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
    assert df["Symbol"][0] == 1
    assert df["Digits"][0] == 5
    assert df["PipPosition"][0] == 4
    assert df["LotSize"][0] == pytest.approx(1000.0)
    assert df["MinVolume"][0] == pytest.approx(10.0)
    assert df["CommissionType"][0] == "UsdPerMillionUsd"
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
def test_catalog_decodes_percentage_and_minimum_commission(spotware):
    symbols = ProtoOASymbolsListRes()
    _add_symbol(symbols, 1, "EURUSD", asset_base=10, asset_quote=20, category=5)
    _add_symbol(symbols, 2, "US 500", asset_base=30, asset_quote=20, category=6)
    assets = ProtoOAAssetListRes()
    for uid, name in ((10, "EUR"), (20, "USD"), (30, "US 500")):
        a = assets.asset.add(); a.assetId = uid; a.name = name; a.displayName = name; a.digits = 2
    classes = ProtoOAAssetClassListRes()
    c = classes.assetClass.add(); c.id = 1; c.name = "Forex"
    d = classes.assetClass.add(); d.id = 2; d.name = "Indices"
    categories = ProtoOASymbolCategoryListRes()
    e = categories.symbolCategory.add(); e.id = 5; e.assetClassId = 1; e.name = "Major"
    f = categories.symbolCategory.add(); f.id = 6; f.assetClassId = 2; f.name = "Default Category"
    specifications = ProtoOASymbolByIdRes()
    fx = specifications.symbol.add(); fx.symbolId = 1; fx.digits = 5; fx.pipPosition = 4; fx.commissionType = 1; fx.preciseTradingCommissionRate = 4_500_000_000
    index = specifications.symbol.add(); index.symbolId = 2; index.digits = 2; index.pipPosition = 0; index.commissionType = 3; index.preciseTradingCommissionRate = 1000
    index.preciseMinCommission = 400_000_000; index.minCommissionType = 2; index.minCommissionAsset = "EUR"
    spotware._responses_.extend([symbols, assets, classes, categories, specifications])
    df = spotware.universe.catalog(legacy=False)
    fx_row, index_row = df.row(0, named=True), df.row(1, named=True)
    assert fx_row["CommissionMode"] == "BaseAssetPerMillionVolume" and fx_row["Commission"] == pytest.approx(45.0)
    assert fx_row["MinCommission"] == 0.0 and fx_row["MinCommissionAsset"] == "USD"
    assert index_row["CommissionMode"] == "PercentageOfVolume" and index_row["Commission"] == pytest.approx(0.01)
    assert index_row["MinCommission"] == pytest.approx(4.0) and index_row["MinCommissionAsset"] == "USD"