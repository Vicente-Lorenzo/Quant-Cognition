import math
import talib

from Library.Utility import IndicatorType, IndicatorConfigurationAPI

class IndicatorsAPI:

    @classmethod
    def find(cls, indicator_type: IndicatorType) -> dict[str, IndicatorConfigurationAPI]:
        return {indicator_id: indicator for indicator_id, indicator in cls.__dict__.items() if isinstance(indicator, IndicatorConfigurationAPI) and indicator.IndicatorType == indicator_type}

    # ==================== BASELINES ====================
    SMA = IndicatorConfigurationAPI(
        Name="Simple Moving Average (Short-Term)",
        IndicatorType=IndicatorType.Baseline,
        Input=lambda market: [market.ClosePrice],
        Parameters={"window": [[5, 50, 5], [-20, +20, 2], [-10, +10, 1]]},
        Constraints=lambda window: window >= 5,
        Function=lambda series, window: talib.SMA(*series, timeperiod=window),
        Output=["Result"],
        FilterBuy=lambda market, indicator, shift: market.ClosePrice.over(indicator.Result, shift),
        FilterSell=lambda market, indicator, shift: market.ClosePrice.under(indicator.Result, shift),
        SignalBuy=lambda market, indicator, shift: market.ClosePrice.crossover(indicator.Result, shift),
        SignalSell=lambda market, indicator, shift: market.ClosePrice.crossunder(indicator.Result, shift))

    EMA = IndicatorConfigurationAPI(
        Name="Exponential Moving Average",
        IndicatorType=IndicatorType.Baseline,
        Input=lambda market: [market.ClosePrice],
        Parameters={"window": [[5, 50, 5], [-20, +20, 2], [-10, +10, 1]]},
        Constraints=lambda window: window >= 5,
        Function=lambda series, window: talib.EMA(*series, timeperiod=window),
        Output=["Result"],
        FilterBuy=lambda market, indicator, shift: market.ClosePrice.over(indicator.Result, shift),
        FilterSell=lambda market, indicator, shift: market.ClosePrice.under(indicator.Result, shift),
        SignalBuy=lambda market, indicator, shift: market.ClosePrice.crossover(indicator.Result, shift),
        SignalSell=lambda market, indicator, shift: market.ClosePrice.crossunder(indicator.Result, shift))

    WMA = IndicatorConfigurationAPI(
        Name="Weighted Moving Average",
        IndicatorType=IndicatorType.Baseline,
        Input=lambda market: [market.ClosePrice],
        Parameters={"window": [[5, 50, 5], [-20, +20, 2], [-10, +10, 1]]},
        Constraints=lambda window: window >= 5,
        Function=lambda series, window: talib.WMA(*series, timeperiod=window),
        Output=["Result"],
        FilterBuy=lambda market, indicator, shift: market.ClosePrice.over(indicator.Result, shift),
        FilterSell=lambda market, indicator, shift: market.ClosePrice.under(indicator.Result, shift),
        SignalBuy=lambda market, indicator, shift: market.ClosePrice.crossover(indicator.Result, shift),
        SignalSell=lambda market, indicator, shift: market.ClosePrice.crossunder(indicator.Result, shift))

    @staticmethod
    def custom_HMA(series, window):
        return talib.WMA(2 * talib.WMA(*series, timeperiod=math.floor(window / 2)) - talib.WMA(*series, timeperiod=window), timeperiod=math.floor(math.sqrt(window)))


    HMA = IndicatorConfigurationAPI(
        Name="Hull Moving Average",
        IndicatorType=IndicatorType.Baseline,
        Input=lambda market: [market.ClosePrice],
        Parameters={"window": [[5, 50, 5], [-20, +20, 2], [-10, +10, 1]]},
        Constraints=lambda window: window >= 5,
        Function=lambda series, window: IndicatorsAPI.custom_HMA(series, window),
        Output=["Result"],
        FilterBuy=lambda market, indicator, shift: market.ClosePrice.over(indicator.Result, shift),
        FilterSell=lambda market, indicator, shift: market.ClosePrice.under(indicator.Result, shift),
        SignalBuy=lambda market, indicator, shift: market.ClosePrice.crossover(indicator.Result, shift),
        SignalSell=lambda market, indicator, shift: market.ClosePrice.crossunder(indicator.Result, shift))

    DEMA = IndicatorConfigurationAPI(
        Name="Double Exponential Moving Average",
        IndicatorType=IndicatorType.Baseline,
        Input=lambda market: [market.ClosePrice],
        Parameters={"window": [[5, 50, 5], [-20, +20, 2], [-10, +10, 1]]},
        Constraints=lambda window: window >= 5,
        Function=lambda series, window: talib.DEMA(*series, timeperiod=window),
        Output=["Result"],
        FilterBuy=lambda market, indicator, shift: market.ClosePrice.over(indicator.Result, shift),
        FilterSell=lambda market, indicator, shift: market.ClosePrice.under(indicator.Result, shift),
        SignalBuy=lambda market, indicator, shift: market.ClosePrice.crossover(indicator.Result, shift),
        SignalSell=lambda market, indicator, shift: market.ClosePrice.crossunder(indicator.Result, shift))

    TEMA = IndicatorConfigurationAPI(
        Name="Triple Exponential Moving Average",
        IndicatorType=IndicatorType.Baseline,
        Input=lambda market: [market.ClosePrice],
        Parameters={"window": [[5, 50, 5], [-20, +20, 2], [-10, +10, 1]]},
        Constraints=lambda window: window >= 5,
        Function=lambda series, window: talib.TEMA(*series, timeperiod=window),
        Output=["Result"],
        FilterBuy=lambda market, indicator, shift: market.ClosePrice.over(indicator.Result, shift),
        FilterSell=lambda market, indicator, shift: market.ClosePrice.under(indicator.Result, shift),
        SignalBuy=lambda market, indicator, shift: market.ClosePrice.crossover(indicator.Result, shift),
        SignalSell=lambda market, indicator, shift: market.ClosePrice.crossunder(indicator.Result, shift))
    
    TRIMA = IndicatorConfigurationAPI(
        Name="Triangular Moving Average",
        IndicatorType=IndicatorType.Baseline,
        Input=lambda market: [market.ClosePrice],
        Parameters={"window": [[5, 50, 5], [-20, +20, 2], [-10, +10, 1]]},
        Constraints=lambda window: window >= 5,
        Function=lambda series, window: talib.TRIMA(*series, timeperiod=window),
        Output=["Result"],
        FilterBuy=lambda market, indicator, shift: market.ClosePrice.over(indicator.Result, shift),
        FilterSell=lambda market, indicator, shift: market.ClosePrice.under(indicator.Result, shift),
        SignalBuy=lambda market, indicator, shift: market.ClosePrice.crossover(indicator.Result, shift),
        SignalSell=lambda market, indicator, shift: market.ClosePrice.crossunder(indicator.Result, shift))

    KAMA = IndicatorConfigurationAPI(
        Name="Kaufman Adaptive Moving Average",
        IndicatorType=IndicatorType.Baseline,
        Input=lambda market: [market.ClosePrice],
        Parameters={"window": [[5, 50, 5], [-20, +20, 2], [-10, +10, 1]]},
        Constraints=lambda window: window >= 5,
        Function=lambda series, window: talib.KAMA(*series, timeperiod=window),
        Output=["Result"],
        FilterBuy=lambda market, indicator, shift: market.ClosePrice.over(indicator.Result, shift),
        FilterSell=lambda market, indicator, shift: market.ClosePrice.under(indicator.Result, shift),
        SignalBuy=lambda market, indicator, shift: market.ClosePrice.crossover(indicator.Result, shift),
        SignalSell=lambda market, indicator, shift: market.ClosePrice.crossunder(indicator.Result, shift))

    # ==================== OVERLAP ====================
    SMAC = IndicatorConfigurationAPI(
        Name="Simple Moving Average Cross",
        IndicatorType=IndicatorType.Overlap,
        Input=lambda market: [market.ClosePrice],
        Parameters={"fast_window": [[5, 50, 5], [-20, +20, 2], [-10, +10, 1]], "slow_window": [[5, 50, 5], [-20, +20, 2], [-10, +10, 1]]},
        Constraints=lambda fast_window, slow_window: 5 <= fast_window < slow_window,
        Function=lambda series, fast_window, slow_window: (talib.SMA(*series, timeperiod=fast_window), talib.SMA(*series, timeperiod=slow_window)),
        Output=["Fast", "Slow"],
        FilterBuy=lambda _, indicator, shift: indicator.Fast.over(indicator.Slow),
        FilterSell=lambda _, indicator, shift: indicator.Fast.under(indicator.Slow),
        SignalBuy=lambda _, indicator, shift: indicator.Fast.crossover(indicator.Slow),
        SignalSell=lambda _, indicator, shift: indicator.Fast.crossunder(indicator.Slow))


    EMAC = IndicatorConfigurationAPI(
        Name="Exponential Moving Average Cross",
        IndicatorType=IndicatorType.Overlap,
        Input=lambda market: [market.ClosePrice],
        Parameters={"fast_window": [[5, 50, 5], [-20, +20, 2], [-10, +10, 1]], "slow_window": [[5, 50, 5], [-20, +20, 2], [-10, +10, 1]]},
        Constraints=lambda fast_window, slow_window: 5 <= fast_window < slow_window,
        Function=lambda series, fast_window, slow_window: (talib.EMA(*series, timeperiod=fast_window), talib.EMA(*series, timeperiod=slow_window)),
        Output=["Fast", "Slow"],
        FilterBuy=lambda _, indicator, shift: indicator.Fast.over(indicator.Slow),
        FilterSell=lambda _, indicator, shift: indicator.Fast.under(indicator.Slow),
        SignalBuy=lambda _, indicator, shift: indicator.Fast.crossover(indicator.Slow),
        SignalSell=lambda _, indicator, shift: indicator.Fast.crossunder(indicator.Slow))

    WMAC = IndicatorConfigurationAPI(
        Name="Weighted Moving Average Cross",
        IndicatorType=IndicatorType.Overlap,
        Input=lambda market: [market.ClosePrice],
        Parameters={"fast_window": [[5, 50, 5], [-20, +20, 2], [-10, +10, 1]], "slow_window": [[5, 50, 5], [-20, +20, 2], [-10, +10, 1]]},
        Constraints=lambda fast_window, slow_window: 5 <= fast_window < slow_window,
        Function=lambda series, fast_window, slow_window: (talib.WMA(*series, timeperiod=fast_window), talib.WMA(*series, timeperiod=slow_window)),
        Output=["Fast", "Slow"],
        FilterBuy=lambda _, indicator, shift: indicator.Fast.over(indicator.Slow),
        FilterSell=lambda _, indicator, shift: indicator.Fast.under(indicator.Slow),
        SignalBuy=lambda _, indicator, shift: indicator.Fast.crossover(indicator.Slow),
        SignalSell=lambda _, indicator, shift: indicator.Fast.crossunder(indicator.Slow))

    HMAC = IndicatorConfigurationAPI(
        Name="Hull Moving Average Cross",
        IndicatorType=IndicatorType.Overlap,
        Input=lambda market: [market.ClosePrice],
        Parameters={"fast_window": [[5, 50, 5], [-20, +20, 2], [-10, +10, 1]], "slow_window": [[5, 50, 5], [-20, +20, 2], [-10, +10, 1]]},
        Constraints=lambda fast_window, slow_window: 5 <= fast_window < slow_window,
        Function=lambda series, fast_window, slow_window: (IndicatorsAPI.custom_HMA(series, fast_window), IndicatorsAPI.custom_HMA(series, slow_window)),
        Output=["Fast", "Slow"],
        FilterBuy=lambda _, indicator, shift: indicator.Fast.over(indicator.Slow),
        FilterSell=lambda _, indicator, shift: indicator.Fast.under(indicator.Slow),
        SignalBuy=lambda _, indicator, shift: indicator.Fast.crossover(indicator.Slow),
        SignalSell=lambda _, indicator, shift: indicator.Fast.crossunder(indicator.Slow))

    DEMAC = IndicatorConfigurationAPI(
        Name="Double Exponential Moving Average Cross",
        IndicatorType=IndicatorType.Overlap,
        Input=lambda market: [market.ClosePrice],
        Parameters={"fast_window": [[5, 50, 5], [-20, +20, 2], [-10, +10, 1]], "slow_window": [[5, 50, 5], [-20, +20, 2], [-10, +10, 1]]},
        Constraints=lambda fast_window, slow_window: 5 <= fast_window < slow_window,
        Function=lambda series, fast_window, slow_window: (talib.DEMA(*series, timeperiod=fast_window), talib.DEMA(*series, timeperiod=slow_window)),
        Output=["Fast", "Slow"],
        FilterBuy=lambda _, indicator, shift: indicator.Fast.over(indicator.Slow),
        FilterSell=lambda _, indicator, shift: indicator.Fast.under(indicator.Slow),
        SignalBuy=lambda _, indicator, shift: indicator.Fast.crossover(indicator.Slow),
        SignalSell=lambda _, indicator, shift: indicator.Fast.crossunder(indicator.Slow))

    TEMAC = IndicatorConfigurationAPI(
        Name="Triple Exponential Moving Average Cross",
        IndicatorType=IndicatorType.Overlap,
        Input=lambda market: [market.ClosePrice],
        Parameters={"fast_window": [[5, 50, 5], [-20, +20, 2], [-10, +10, 1]], "slow_window": [[5, 50, 5], [-20, +20, 2], [-10, +10, 1]]},
        Constraints=lambda fast_window, slow_window: 5 <= fast_window < slow_window,
        Function=lambda series, fast_window, slow_window: (talib.TEMA(*series, timeperiod=fast_window), talib.TEMA(*series, timeperiod=slow_window)),
        Output=["Fast", "Slow"],
        FilterBuy=lambda _, indicator, shift: indicator.Fast.over(indicator.Slow),
        FilterSell=lambda _, indicator, shift: indicator.Fast.under(indicator.Slow),
        SignalBuy=lambda _, indicator, shift: indicator.Fast.crossover(indicator.Slow),
        SignalSell=lambda _, indicator, shift: indicator.Fast.crossunder(indicator.Slow))

    TRIMAC = IndicatorConfigurationAPI(
        Name="Triangular Moving Average Cross",
        IndicatorType=IndicatorType.Overlap,
        Input=lambda market: [market.ClosePrice],
        Parameters={"fast_window": [[5, 50, 5], [-20, +20, 2], [-10, +10, 1]], "slow_window": [[5, 50, 5], [-20, +20, 2], [-10, +10, 1]]},
        Constraints=lambda fast_window, slow_window: 5 <= fast_window < slow_window,
        Function=lambda series, fast_window, slow_window: (talib.TRIMA(*series, timeperiod=fast_window), talib.TRIMA(*series, timeperiod=slow_window)),
        Output=["Fast", "Slow"],
        FilterBuy=lambda _, indicator, shift: indicator.Fast.over(indicator.Slow),
        FilterSell=lambda _, indicator, shift: indicator.Fast.under(indicator.Slow),
        SignalBuy=lambda _, indicator, shift: indicator.Fast.crossover(indicator.Slow),
        SignalSell=lambda _, indicator, shift: indicator.Fast.crossunder(indicator.Slow))

    KAMAC = IndicatorConfigurationAPI(
        Name="Kaufman Adaptive Moving Average Cross",
        IndicatorType=IndicatorType.Overlap,
        Input=lambda market: [market.ClosePrice],
        Parameters={"fast_window": [[5, 50, 5], [-20, +20, 2], [-10, +10, 1]], "slow_window": [[5, 50, 5], [-20, +20, 2], [-10, +10, 1]]},
        Constraints=lambda fast_window, slow_window: 5 <= fast_window < slow_window,
        Function=lambda series, fast_window, slow_window: (talib.KAMA(*series, timeperiod=fast_window), talib.KAMA(*series, timeperiod=slow_window)),
        Output=["Fast", "Slow"],
        FilterBuy=lambda _, indicator, shift: indicator.Fast.over(indicator.Slow),
        FilterSell=lambda _, indicator, shift: indicator.Fast.under(indicator.Slow),
        SignalBuy=lambda _, indicator, shift: indicator.Fast.crossover(indicator.Slow),
        SignalSell=lambda _, indicator, shift: indicator.Fast.crossunder(indicator.Slow))

    # ==================== Momentum ====================

    AROON = IndicatorConfigurationAPI(
        Name="Aroon Up and Down Indicator",
        IndicatorType=IndicatorType.Momentum,
        Input=lambda market: [market.HighPrice, market.LowPrice],
        Parameters={"window": [[5, 50, 5], [-20, +20, 2], [-10, +10, 1]]},
        Constraints=lambda window: window >= 5,
        Function=lambda series, window: talib.AROON(*series, timeperiod=window),
        Output=["Down", "Up"],
        FilterBuy=lambda _, indicator, shift: indicator.Up.over(indicator.Down),
        FilterSell=lambda _, indicator, shift: indicator.Down.over(indicator.Up),
        SignalBuy=lambda _, indicator, shift: indicator.Up.crossover(indicator.Down),
        SignalSell=lambda _, indicator, shift: indicator.Down.crossunder(indicator.Up))

    CCI = IndicatorConfigurationAPI(
        Name="Commodity Channel Index",
        IndicatorType=IndicatorType.Momentum,
        Input=lambda market: [market.HighPrice, market.LowPrice, market.ClosePrice],
        Parameters={"window": [[5, 50, 5], [-20, +20, 2], [-10, +10, 1]]},
        Constraints=lambda window: window >= 5,
        Function=lambda series, window: talib.CCI(*series, timeperiod=window),
        Output=["Result"],
        FilterBuy=lambda _, indicator, shift: indicator.Result.over(0, shift),
        FilterSell=lambda _, indicator, shift: indicator.Result.under(0, shift),
        SignalBuy=lambda _, indicator, shift: indicator.Result.crossover(0, shift),
        SignalSell=lambda _, indicator, shift: indicator.Result.crossunder(0, shift))

    MACD = IndicatorConfigurationAPI(
        Name="Moving Average Convergence Divergence",
        IndicatorType=IndicatorType.Momentum,
        Input=lambda market: [market.ClosePrice],
        Parameters={"fast_window": [[5, 50, 5], [-20, +20, 2], [-10, +10, 1]], "slow_window": [[5, 50, 5], [-20, +20, 2], [-10, +10, 1]], "signal_window": [[5, 50, 5], [-20, +20, 2], [-10, +10, 1]]},
        Constraints=lambda fast_window, slow_window, signal_window: 5 <= signal_window < fast_window < slow_window,
        Function=lambda series, fast_window, slow_window, signal_window: talib.MACD(*series, fastperiod=fast_window, slowperiod=slow_window, signalperiod=signal_window),
        Output=["MACD", "Signal", "Histogram"],
        FilterBuy=lambda _, indicator, shift: indicator.MACD.over(indicator.Signal, shift),
        FilterSell=lambda _, indicator, shift: indicator.MACD.under(indicator.Signal, shift),
        SignalBuy=lambda _, indicator, shift: indicator.MACD.crossover(indicator.Signal, shift),
        SignalSell=lambda _, indicator, shift: indicator.MACD.crossunder(indicator.Signal, shift))

    PSAR = IndicatorConfigurationAPI(
        Name="Parabolic SAR",
        IndicatorType=IndicatorType.Momentum,
        Input=lambda market: [market.HighPrice, market.LowPrice],
        Parameters={"acceleration": [[0.01, 0.2, 0.01], [-0.05, +0.05, 0.01], [-0.02, +0.02, 0.01]], "maximum": [[0.1, 0.5, 0.05], [-0.1, +0.1, 0.01], [-0.05, +0.05, 0.01]]},
        Constraints=lambda acceleration, maximum: 0.0 < acceleration < maximum,
        Function=lambda series, acceleration, maximum: talib.SAR(*series, acceleration=acceleration, maximum=maximum),
        Output=["PSAR"],
        FilterBuy=lambda market, indicator, shift: market.ClosePrice.over(indicator.PSAR, shift),
        FilterSell=lambda market, indicator, shift: market.ClosePrice.under(indicator.PSAR, shift),
        SignalBuy=lambda market, indicator, shift: market.ClosePrice.crossover(indicator.PSAR, shift),
        SignalSell=lambda market, indicator, shift: market.ClosePrice.crossunder(indicator.PSAR, shift))

    # BBANDS = Technical(
    #     Name="Bollinger Bands",
    #     TechnicalType=TechnicalType.Volatility,
    #     Input=lambda market: [market.ClosePrice],
    #     Parameters={"period": [5, 300, 1], "nbdevup": [1.0, 3.0, 0.1], "nbdevdn": [1.0, 3.0, 0.1], "matype": [0, 1, 2, 3, 4]},
    #     Constraints=lambda period, nbdevup, nbdevdn, matype: True,
    #     Function=talib.BBANDS,
    #     Output=["Upper", "Middle", "Lower"],
    #     FilterBuy=lambda market, indicator, shift: False,
    #     FilterSell=lambda market, indicator, shift: False,
    #     SignalBuy=lambda market, indicator, shift: False,
    #     SignalSell=lambda market, indicator, shift: False)

    # ==================== Volume ====================
    # AD = Technical(
    #     Name="Chaikin A/D Line",
    #     TechnicalType=TechnicalType.Volume,
    #     Input=lambda market: [market.HighPrice, market.LowPrice, market.ClosePrice, market.Volume],
    #     Parameters={},
    #     Constraints=lambda: True,
    #     Function=lambda series: (talib.AD(*series),),
    #     Output=["AD"],
    #     FilterBuy=lambda _, indicator, shift: indicator.AD.rising(),
    #     FilterSell=lambda _, indicator, shift: indicator.AD.falling(),
    #     SignalBuy=lambda _, indicator, shift: indicator.AD.crossover(indicator.AD.sma(10)),
    #     SignalSell=lambda _, indicator, shift: indicator.AD.crossunder(indicator.AD.sma(10)))

    ADOSC = IndicatorConfigurationAPI(
        Name="Chaikin A/D Oscillator",
        IndicatorType=IndicatorType.Volume,
        Input=lambda market: [market.HighPrice, market.LowPrice, market.ClosePrice, market.TickVolume],
        Parameters={"fast_window": [[5, 50, 5], [-20, +20, 2], [-10, +10, 1]], "slow_window": [[5, 50, 5], [-20, +20, 2], [-10, +10, 1]]},
        Constraints=lambda fast_window, slow_window: 5 <= fast_window < slow_window,
        Function=lambda series, fast_window, slow_window: (talib.ADOSC(*series, fastperiod=fast_window, slowperiod=slow_window),),
        Output=["ADOSC"],
        FilterBuy=lambda _, indicator, shift: indicator.ADOSC.over(0.0, shift),
        FilterSell=lambda _, indicator, shift: indicator.ADOSC.over(0.0, shift),
        SignalBuy=lambda _, indicator, shift: indicator.ADOSC.crossover(0.0, shift),
        SignalSell=lambda _, indicator, shift: indicator.ADOSC.crossover(0.0, shift))

    # OBV = Technical(
    #     Name="On Balance Volume",
    #     TechnicalType=TechnicalType.Volume,
    #     Input=lambda market: [market.ClosePrice, market.Volume],
    #     Parameters={},
    #     Constraints=lambda: True,
    #     Function=lambda series: (talib.OBV(*series),),
    #     Output=["OBV"],
    #     FilterBuy=lambda _, indicator, shift: indicator.OBV.rising(),
    #     FilterSell=lambda _, indicator, shift: indicator.OBV.falling(),
    #     SignalBuy=lambda _, indicator, shift: indicator.OBV.crossover(indicator.OBV.sma(10)),
    #     SignalSell=lambda _, indicator, shift: indicator.OBV.crossunder(indicator.OBV.sma(10)))

    # ==================== Volatility ====================
    ATR = IndicatorConfigurationAPI(
        Name="Average True Range",
        IndicatorType=IndicatorType.Volatility,
        Input=lambda market: [market.HighPrice, market.LowPrice, market.ClosePrice],
        Parameters={"window": [[5, 50, 5], [-20, +20, 2], [-10, +10, 1]]},
        Constraints=lambda window: window >= 5,
        Function=lambda series, window: talib.ATR(*series, timeperiod=window),
        Output=["Result"],
        FilterBuy=lambda market, indicator, shift: False,
        FilterSell=lambda market, indicator, shift: False,
        SignalBuy=lambda market, indicator, shift: False,
        SignalSell=lambda market, indicator, shift: False)

    # ==================== Other ====================
    TT = IndicatorConfigurationAPI(
        Name="True Filter and True Signal",
        IndicatorType=IndicatorType.Other,
        Input=lambda market: [market.ClosePrice],
        Parameters={},
        Constraints=lambda _: True,
        Function=lambda series: series,
        Output=["Result"],
        FilterBuy=lambda *_: True,
        FilterSell=lambda *_: True,
        SignalBuy=lambda *_: True,
        SignalSell=lambda*_: True)

    TF = IndicatorConfigurationAPI(
        Name="True Filter and False Signal",
        IndicatorType=IndicatorType.Other,
        Input=lambda market: [market.ClosePrice],
        Parameters={},
        Constraints=lambda _: True,
        Function=lambda series: series,
        Output=["Result"],
        FilterBuy=lambda *_: True,
        FilterSell=lambda *_: True,
        SignalBuy=lambda *_: False,
        SignalSell=lambda*_: False)

    FT = IndicatorConfigurationAPI(
        Name="False Filter and True Signal",
        IndicatorType=IndicatorType.Other,
        Input=lambda market: [market.ClosePrice],
        Parameters={},
        Constraints=lambda _: True,
        Function=lambda series: series,
        Output=["Result"],
        FilterBuy=lambda *_: False,
        FilterSell=lambda *_: False,
        SignalBuy=lambda *_: True,
        SignalSell=lambda*_: True)

    FF = IndicatorConfigurationAPI(
        Name="False Filter and False Signal",
        IndicatorType=IndicatorType.Other,
        Input=lambda market: [market.ClosePrice],
        Parameters={},
        Constraints=lambda _: True,
        Function=lambda series: series,
        Output=["Result"],
        FilterBuy=lambda *_: False,
        FilterSell=lambda *_: False,
        SignalBuy=lambda *_: False,
        SignalSell=lambda*_: False)