from typing import Union

from Library.Database.Dataframe import pd, pl
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