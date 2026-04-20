from Library.Database.Dataframe import pd, pl
from Library.Utility.Service import ServiceAPI
from Library.Utility.Typing import MISSING, Missing

class UniverseAPI(ServiceAPI):

    def tickers(self,
                archived: bool = False,
                legacy: bool | Missing = MISSING) -> pd.DataFrame | pl.DataFrame:
        from ctrader_open_api import Protobuf
        def _fetch_():
            request = Protobuf.get("ProtoOASymbolsListReq",
                                   ctidTraderAccountId=self._api_._account_id_,
                                   includeArchivedSymbols=bool(archived))
            response = self._api_._send_(request)
            data = []
            for s in response.symbol:
                data.append({
                    "SecurityUID": s.symbolId,
                    "TickerUID": s.symbolName,
                    "BaseAssetId": s.baseAssetId,
                    "QuoteAssetId": s.quoteAssetId,
                    "CategoryId": s.symbolCategoryId,
                    "Description": s.description,
                    "Enabled": s.enabled,
                    "Archived": False
                })
            for s in response.archivedSymbol:
                data.append({
                    "SecurityUID": s.symbolId,
                    "TickerUID": s.name,
                    "BaseAssetId": None,
                    "QuoteAssetId": None,
                    "CategoryId": None,
                    "Description": s.description,
                    "Enabled": False,
                    "Archived": True
                })
            return self._api_.frame(data, legacy=legacy)
        timer, df = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Tickers Operation: Fetched {len(df)} tickers ({timer.result()})")
        return df

    def ticker(self,
               ids: int | list[int],
               legacy: bool | Missing = MISSING) -> pd.DataFrame | pl.DataFrame:
        from ctrader_open_api import Protobuf
        ids_list = self._api_.flatten(ids)
        def _fetch_():
            request = Protobuf.get("ProtoOASymbolByIdReq",
                                   ctidTraderAccountId=self._api_._account_id_,
                                   symbolId=[int(i) for i in ids_list])
            response = self._api_._send_(request)
            data = []
            for s in list(response.symbol) + list(response.archivedSymbol):
                data.append({
                    "SecurityUID": s.symbolId,
                    "Digits": s.digits,
                    "PipPosition": s.pipPosition,
                    "LotSize": s.lotSize,
                    "MinVolume": s.minVolume,
                    "MaxVolume": s.maxVolume,
                    "StepVolume": s.stepVolume,
                    "MaxExposure": s.maxExposure,
                    "Commission": s.commission,
                    "CommissionType": s.commissionType,
                    "MinCommission": s.minCommission,
                    "MinCommissionType": s.minCommissionType,
                    "MinCommissionAsset": s.minCommissionAsset,
                    "RolloverCommission": s.rolloverCommission,
                    "SkipRolloverDays": s.skipRolloverDays,
                    "PreciseTradingCommissionRate": s.preciseTradingCommissionRate,
                    "PreciseMinCommission": s.preciseMinCommission,
                    "SwapLong": s.swapLong,
                    "SwapShort": s.swapShort,
                    "SwapCalculationType": s.swapCalculationType,
                    "SwapRollover3Days": s.swapRollover3Days,
                    "SwapPeriod": s.swapPeriod,
                    "SwapTime": s.swapTime,
                    "ChargeSwapAtWeekends": s.chargeSwapAtWeekends,
                    "SlDistance": s.slDistance,
                    "TpDistance": s.tpDistance,
                    "GslDistance": s.gslDistance,
                    "GslCharge": s.gslCharge,
                    "DistanceSetIn": s.distanceSetIn,
                    "TradingMode": s.tradingMode,
                    "EnableShortSelling": s.enableShortSelling,
                    "GuaranteedStopLoss": s.guaranteedStopLoss,
                    "LeverageId": s.leverageId,
                    "PnLConversionFeeRate": s.pnlConversionFeeRate,
                    "ScheduleTimeZone": s.scheduleTimeZone
                })
            return self._api_.frame(data, legacy=legacy)
        timer, df = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Ticker Operation: Fetched {len(df)} ticker details ({timer.result()})")
        return df

    def assets(self, legacy: bool | Missing = MISSING) -> pd.DataFrame | pl.DataFrame:
        from ctrader_open_api import Protobuf
        def _fetch_():
            request = Protobuf.get("ProtoOAAssetListReq",
                                   ctidTraderAccountId=self._api_._account_id_)
            response = self._api_._send_(request)
            data = [{
                "AssetId": a.assetId,
                "Name": a.name,
                "DisplayName": a.displayName,
                "Digits": a.digits
            } for a in response.asset]
            return self._api_.frame(data, legacy=legacy)
        timer, df = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Assets Operation: Fetched {len(df)} assets ({timer.result()})")
        return df

    def classes(self, legacy: bool | Missing = MISSING) -> pd.DataFrame | pl.DataFrame:
        from ctrader_open_api import Protobuf
        def _fetch_():
            request = Protobuf.get("ProtoOAAssetClassListReq",
                                   ctidTraderAccountId=self._api_._account_id_)
            response = self._api_._send_(request)
            data = [{
                "AssetClassId": c.id,
                "Name": c.name
            } for c in response.assetClass]
            return self._api_.frame(data, legacy=legacy)
        timer, df = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Classes Operation: Fetched {len(df)} asset classes ({timer.result()})")
        return df

    def categories(self, legacy: bool | Missing = MISSING) -> pd.DataFrame | pl.DataFrame:
        from ctrader_open_api import Protobuf
        def _fetch_():
            request = Protobuf.get("ProtoOASymbolCategoryListReq",
                                   ctidTraderAccountId=self._api_._account_id_)
            response = self._api_._send_(request)
            data = [{
                "CategoryId": c.id,
                "AssetClassId": c.assetClassId,
                "Name": c.name
            } for c in response.symbolCategory]
            return self._api_.frame(data, legacy=legacy)
        timer, df = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Categories Operation: Fetched {len(df)} categories ({timer.result()})")
        return df
