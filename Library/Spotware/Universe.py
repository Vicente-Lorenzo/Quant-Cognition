from typing import Callable, Union

from Library.Database.Dataframe import pd, pl
from Library.Spotware.Client import ClientAPI
from Library.Spotware.Messages import PROTO_OA_SYMBOL_CHANGED_EVENT
from Library.Utility.Service import ServiceAPI
from Library.Utility.Typing import MISSING, Missing

class UniverseAPI(ServiceAPI):

    def tickers(self,
                archived: bool = False,
                legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame]:
        def _fetch_():
            response = self._api_._request_("ProtoOASymbolsListReq", includeArchivedSymbols=bool(archived))
            rows = [{
                "Symbol": symbol.symbolId,
                "Ticker": symbol.symbolName,
                "BaseAssetId": symbol.baseAssetId,
                "QuoteAssetId": symbol.quoteAssetId,
                "CategoryId": symbol.symbolCategoryId,
                "Description": symbol.description,
                "Enabled": symbol.enabled,
                "Archived": False
            } for symbol in response.symbol]
            rows += [{
                "Symbol": symbol.symbolId,
                "Ticker": symbol.name,
                "BaseAssetId": None,
                "QuoteAssetId": None,
                "CategoryId": None,
                "Description": symbol.description,
                "Enabled": False,
                "Archived": True
            } for symbol in response.archivedSymbol]
            return self._api_.frame(rows, legacy=legacy)
        timer, df = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Tickers Operation: Fetched {len(df)} tickers ({timer.result()})")
        return df

    def ticker(self,
               ids: Union[int, list[int]],
               legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame]:
        symbols = [int(i) for i in self._api_.flatten(ids)]
        def _fetch_():
            api = self._api_
            response = api._request_("ProtoOASymbolByIdReq", symbolId=symbols)
            rows = [{
                "Symbol": symbol.symbolId,
                "Digits": symbol.digits,
                "PipPosition": symbol.pipPosition,
                "LotSize": api._units_(symbol.lotSize),
                "MinVolume": api._units_(symbol.minVolume),
                "MaxVolume": api._units_(symbol.maxVolume),
                "StepVolume": api._units_(symbol.stepVolume),
                "MaxExposure": symbol.maxExposure,
                "Commission": symbol.commission,
                "CommissionType": api._named_(symbol, "commissionType"),
                "MinCommission": symbol.minCommission,
                "MinCommissionType": api._named_(symbol, "minCommissionType"),
                "MinCommissionAsset": symbol.minCommissionAsset,
                "RolloverCommission": symbol.rolloverCommission,
                "SkipRolloverDays": symbol.skipRolloverDays,
                "PreciseTradingCommissionRate": symbol.preciseTradingCommissionRate,
                "PreciseMinCommission": symbol.preciseMinCommission,
                "SwapLong": symbol.swapLong,
                "SwapShort": symbol.swapShort,
                "SwapCalculationType": api._named_(symbol, "swapCalculationType"),
                "SwapRollover3Days": api._named_(symbol, "swapRollover3Days"),
                "SwapPeriod": symbol.swapPeriod,
                "SwapTime": symbol.swapTime,
                "SkipSwapPeriods": symbol.skipSWAPPeriods,
                "ChargeSwapAtWeekends": symbol.chargeSwapAtWeekends,
                "SlDistance": symbol.slDistance,
                "TpDistance": symbol.tpDistance,
                "GslDistance": symbol.gslDistance,
                "GslCharge": symbol.gslCharge,
                "DistanceSetIn": api._named_(symbol, "distanceSetIn"),
                "TradingMode": api._named_(symbol, "tradingMode"),
                "EnableShortSelling": symbol.enableShortSelling,
                "GuaranteedStopLoss": symbol.guaranteedStopLoss,
                "LeverageId": symbol.leverageId,
                "PnLConversionFeeRate": symbol.pnlConversionFeeRate,
                "ScheduleTimeZone": symbol.scheduleTimeZone
            } for symbol in response.symbol]
            return api.frame(rows, legacy=legacy)
        timer, df = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Ticker Operation: Fetched {len(df)} ticker details ({timer.result()})")
        return df

    def assets(self, legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame]:
        def _fetch_():
            response = self._api_._request_("ProtoOAAssetListReq")
            rows = [{"AssetId": asset.assetId, "Name": asset.name, "DisplayName": asset.displayName, "Digits": asset.digits} for asset in response.asset]
            return self._api_.frame(rows, legacy=legacy)
        timer, df = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Assets Operation: Fetched {len(df)} assets ({timer.result()})")
        return df

    def classes(self, legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame]:
        def _fetch_():
            response = self._api_._request_("ProtoOAAssetClassListReq")
            rows = [{"AssetClassId": group.id, "Name": group.name} for group in response.assetClass]
            return self._api_.frame(rows, legacy=legacy)
        timer, df = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Classes Operation: Fetched {len(df)} asset classes ({timer.result()})")
        return df

    def categories(self, legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame]:
        def _fetch_():
            response = self._api_._request_("ProtoOASymbolCategoryListReq")
            rows = [{"CategoryId": category.id, "AssetClassId": category.assetClassId, "Name": category.name} for category in response.symbolCategory]
            return self._api_.frame(rows, legacy=legacy)
        timer, df = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Categories Operation: Fetched {len(df)} categories ({timer.result()})")
        return df

    @staticmethod
    def _primary_(group: Union[str, None]) -> Union[str, None]:
        primaries = {"Forex": "Forex", "Metals": "Metal", "Indices": "Index", "Energies": "Energy", "EU Shares": "Stock", "US Shares": "Stock", "Asia/Pacific Shares": "Stock",
                     "iShares ETFs": "ETF", "Powershares ETFs": "ETF", "Cryptocurrency": "Crypto"}
        return primaries.get(group, group)

    @staticmethod
    def _country_(group: Union[str, None], category: Union[str, None]) -> Union[str, None]:
        if group in ("US Shares", "iShares ETFs", "Powershares ETFs"): return "United States"
        if group in ("EU Shares", "Asia/Pacific Shares") and category and category != "Default Category": return category
        return None

    @staticmethod
    def _mode_(commission: Union[str, None]) -> Union[str, None]:
        modes = {"UsdPerMillionUsd": "BaseAssetPerMillionVolume", "UsdPerLot": "BaseAssetPerOneLot", "PercentageOfValue": "PercentageOfVolume", "QuoteCcyPerLot": "QuoteAssetPerOneLot"}
        return modes.get(commission)

    def catalog(self, archived: bool = False, legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame]:
        symbols = self.tickers(archived=archived, legacy=False)
        assets = {row["AssetId"]: row for row in self.assets(legacy=False).iter_rows(named=True)}
        groups = {row["AssetClassId"]: row["Name"] for row in self.classes(legacy=False).iter_rows(named=True)}
        categories = {row["CategoryId"]: (groups.get(row["AssetClassId"]), row["Name"]) for row in self.categories(legacy=False).iter_rows(named=True)}
        current = symbols.filter(~pl.col("Archived"))["Symbol"].to_list()
        specifications = {}
        for start in range(0, len(current), 100):
            for row in self.ticker(current[start:start + 100], legacy=False).iter_rows(named=True): specifications[row["Symbol"]] = row
        rows = []
        for symbol in symbols.iter_rows(named=True):
            group, category = categories.get(symbol["CategoryId"], (None, None))
            base, quote = assets.get(symbol["BaseAssetId"], {}), assets.get(symbol["QuoteAssetId"], {})
            specification = specifications.get(symbol["Symbol"], {})
            pip = specification.get("PipPosition")
            digits = specification.get("Digits")
            rate, minimum = specification.get("PreciseTradingCommissionRate"), specification.get("PreciseMinCommission")
            scale = 100_000 if specification.get("CommissionType") == "PercentageOfValue" else 100_000_000
            rows.append({
                "Symbol": symbol["Symbol"],
                "Ticker": symbol["Ticker"],
                "Description": symbol["Description"],
                "Primary": self._primary_(group),
                "Type": "Spot" if self._primary_(group) == "Forex" else "CFD",
                "Country": self._country_(group, category),
                "BaseAsset": base.get("Name"),
                "BaseName": base.get("DisplayName"),
                "QuoteAsset": quote.get("Name"),
                "QuoteName": quote.get("DisplayName"),
                "Status": "Archived" if symbol["Archived"] else "Enabled" if symbol["Enabled"] else "Disabled",
                "Digits": digits,
                "PointSize": 10.0 ** -digits if digits is not None else None,
                "PipSize": 10.0 ** -pip if pip is not None else None,
                "LotSize": specification.get("LotSize"),
                "VolumeMin": specification.get("MinVolume"),
                "VolumeMax": specification.get("MaxVolume"),
                "VolumeStep": specification.get("StepVolume"),
                "CommissionMode": self._mode_(specification.get("CommissionType")),
                "Commission": rate / scale if rate is not None else None,
                "MinCommission": minimum / 100_000_000 if minimum is not None else None,
                "MinCommissionAsset": quote.get("Name") if specification.get("MinCommissionType") == "QuoteCurrency" else specification.get("MinCommissionAsset"),
                "ConversionFee": specification.get("PnLConversionFeeRate") / 100 if specification.get("PnLConversionFeeRate") is not None else None,
                "SwapMode": specification.get("SwapCalculationType"),
                "SwapLong": specification.get("SwapLong"),
                "SwapShort": specification.get("SwapShort"),
                "SwapPeriod": specification.get("SwapPeriod"),
                "SwapTime": specification.get("SwapTime"),
                "SwapSkip": specification.get("SkipSwapPeriods"),
                "SwapExtraDay": specification.get("SwapRollover3Days"),
                "SwapWeekends": specification.get("ChargeSwapAtWeekends"),
                "TradingMode": specification.get("TradingMode")
            })
        self._log_.info(lambda: f"Catalog Operation: Fetched {len(rows)} Symbols · {len(specifications)} Term Sheets")
        return self._api_.frame(rows, legacy=legacy)

    def changes(self, callback: Callable[[list], None]) -> Callable[[], None]:
        def _handler_(message) -> None:
            if getattr(message, "payloadType", None) != PROTO_OA_SYMBOL_CHANGED_EVENT: return
            callback([int(symbol) for symbol in ClientAPI.payload(message).symbolId])
        self._api_.connect()
        self._api_._subscribe_(_handler_)
        return lambda: self._api_._unsubscribe_(_handler_)