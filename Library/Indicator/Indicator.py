from __future__ import annotations

from typing import Union, TYPE_CHECKING
from Library.Database.Enumeration import Enumeration

if TYPE_CHECKING:
    from Library.Indicator.Technical.Technical import TechnicalAPI
    from Library.Indicator.Fundamental.Fundamental import FundamentalAPI
    from Library.Indicator.Sentimental.Sentimental import SentimentalAPI

class IndicatorMode(Enumeration):
    Off = 0
    Filter = 1
    Signal = 2

def parse_technical(parameters: Union[dict, None]) -> TechnicalAPI:
    from Library.Indicator.Technical import TechnicalAPI
    if not parameters:
        return TechnicalAPI(name="Technical", window=None, mode=IndicatorMode.Off)
    
    indicators = {}
    for name, config in parameters.items():
        if not config: continue
        acronym = config[0]
        match acronym:
            case "SMA":
                from Library.Indicator.Technical.Baseline.SMA import SimpleMovingAverageAPI
                window = config[1] if len(config) > 1 else 14
                mode_val = config[2] if len(config) > 2 else IndicatorMode.Off
                indicators[name] = SimpleMovingAverageAPI(name=name, window=window, mode=IndicatorMode.parse(mode_val))
            case "EMA":
                from Library.Indicator.Technical.Baseline.EMA import ExponentialMovingAverageAPI
                window = config[1] if len(config) > 1 else 14
                mode_val = config[2] if len(config) > 2 else IndicatorMode.Off
                indicators[name] = ExponentialMovingAverageAPI(name=name, window=window, mode=IndicatorMode.parse(mode_val))
            case "WMA":
                from Library.Indicator.Technical.Baseline.WMA import WeightedMovingAverageAPI
                window = config[1] if len(config) > 1 else 14
                mode_val = config[2] if len(config) > 2 else IndicatorMode.Off
                indicators[name] = WeightedMovingAverageAPI(name=name, window=window, mode=IndicatorMode.parse(mode_val))
            case "HMA":
                from Library.Indicator.Technical.Baseline.HMA import HullMovingAverageAPI
                window = config[1] if len(config) > 1 else 14
                mode_val = config[2] if len(config) > 2 else IndicatorMode.Off
                indicators[name] = HullMovingAverageAPI(name=name, window=window, mode=IndicatorMode.parse(mode_val))
            case "TRIMA":
                from Library.Indicator.Technical.Baseline.TRIMA import TriangularMovingAverageAPI
                window = config[1] if len(config) > 1 else 14
                mode_val = config[2] if len(config) > 2 else IndicatorMode.Off
                indicators[name] = TriangularMovingAverageAPI(name=name, window=window, mode=IndicatorMode.parse(mode_val))
            case "KAMA":
                from Library.Indicator.Technical.Baseline.KAMA import KaufmanAdaptiveMovingAverageAPI
                window = config[1] if len(config) > 1 else 14
                mode_val = config[2] if len(config) > 2 else IndicatorMode.Off
                indicators[name] = KaufmanAdaptiveMovingAverageAPI(name=name, window=window, mode=IndicatorMode.parse(mode_val))
            case "DMA":
                from Library.Indicator.Technical.Baseline.DMA import DoubleMovingAverageAPI
                from Library.Indicator.Technical.Baseline.MA import MovingAverageType
                window = config[1] if len(config) > 1 else 14
                ma_type = MovingAverageType.parse(config[2]) if len(config) > 2 else MovingAverageType.Exponential
                mode_val = config[3] if len(config) > 3 else IndicatorMode.Off
                indicators[name] = DoubleMovingAverageAPI(name=name, window=window, ma_type=ma_type, mode=IndicatorMode.parse(mode_val))
            case "TMA":
                from Library.Indicator.Technical.Baseline.TMA import TripleMovingAverageAPI
                from Library.Indicator.Technical.Baseline.MA import MovingAverageType
                window = config[1] if len(config) > 1 else 14
                ma_type = MovingAverageType.parse(config[2]) if len(config) > 2 else MovingAverageType.Exponential
                mode_val = config[3] if len(config) > 3 else IndicatorMode.Off
                indicators[name] = TripleMovingAverageAPI(name=name, window=window, ma_type=ma_type, mode=IndicatorMode.parse(mode_val))
            case "SMAC":
                from Library.Indicator.Technical.Overlap.SMAC import SimpleMovingAverageCrossAPI
                fast = config[1] if len(config) > 1 else 5
                slow = config[2] if len(config) > 2 else 20
                mode_val = config[3] if len(config) > 3 else IndicatorMode.Off
                indicators[name] = SimpleMovingAverageCrossAPI(name=name, fast_window=fast, slow_window=slow, mode=IndicatorMode.parse(mode_val))
            case "EMAC":
                from Library.Indicator.Technical.Overlap.EMAC import ExponentialMovingAverageCrossAPI
                fast = config[1] if len(config) > 1 else 5
                slow = config[2] if len(config) > 2 else 20
                mode_val = config[3] if len(config) > 3 else IndicatorMode.Off
                indicators[name] = ExponentialMovingAverageCrossAPI(name=name, fast_window=fast, slow_window=slow, mode=IndicatorMode.parse(mode_val))
            case "WMAC":
                from Library.Indicator.Technical.Overlap.WMAC import WeightedMovingAverageCrossAPI
                fast = config[1] if len(config) > 1 else 5
                slow = config[2] if len(config) > 2 else 20
                mode_val = config[3] if len(config) > 3 else IndicatorMode.Off
                indicators[name] = WeightedMovingAverageCrossAPI(name=name, fast_window=fast, slow_window=slow, mode=IndicatorMode.parse(mode_val))
            case "HMAC":
                from Library.Indicator.Technical.Overlap.HMAC import HullMovingAverageCrossAPI
                fast = config[1] if len(config) > 1 else 5
                slow = config[2] if len(config) > 2 else 20
                mode_val = config[3] if len(config) > 3 else IndicatorMode.Off
                indicators[name] = HullMovingAverageCrossAPI(name=name, fast_window=fast, slow_window=slow, mode=IndicatorMode.parse(mode_val))
            case "TRIMAC":
                from Library.Indicator.Technical.Overlap.TRIMAC import TriangularMovingAverageCrossAPI
                fast = config[1] if len(config) > 1 else 5
                slow = config[2] if len(config) > 2 else 20
                mode_val = config[3] if len(config) > 3 else IndicatorMode.Off
                indicators[name] = TriangularMovingAverageCrossAPI(name=name, fast_window=fast, slow_window=slow, mode=IndicatorMode.parse(mode_val))
            case "KAMAC":
                from Library.Indicator.Technical.Overlap.KAMAC import KaufmanAdaptiveMovingAverageCrossAPI
                fast = config[1] if len(config) > 1 else 5
                slow = config[2] if len(config) > 2 else 20
                mode_val = config[3] if len(config) > 3 else IndicatorMode.Off
                indicators[name] = KaufmanAdaptiveMovingAverageCrossAPI(name=name, fast_window=fast, slow_window=slow, mode=IndicatorMode.parse(mode_val))
            case "DMAC":
                from Library.Indicator.Technical.Overlap.DMAC import DoubleMovingAverageCrossAPI
                from Library.Indicator.Technical.Baseline.MA import MovingAverageType
                fast = config[1] if len(config) > 1 else 5
                slow = config[2] if len(config) > 2 else 20
                ma_type = MovingAverageType.parse(config[3]) if len(config) > 3 else MovingAverageType.Exponential
                mode_val = config[4] if len(config) > 4 else IndicatorMode.Off
                indicators[name] = DoubleMovingAverageCrossAPI(name=name, fast_window=fast, slow_window=slow, ma_type=ma_type, mode=IndicatorMode.parse(mode_val))
            case "TMAC":
                from Library.Indicator.Technical.Overlap.TMAC import TripleMovingAverageCrossAPI
                from Library.Indicator.Technical.Baseline.MA import MovingAverageType
                fast = config[1] if len(config) > 1 else 5
                slow = config[2] if len(config) > 2 else 20
                ma_type = MovingAverageType.parse(config[3]) if len(config) > 3 else MovingAverageType.Exponential
                mode_val = config[4] if len(config) > 4 else IndicatorMode.Off
                indicators[name] = TripleMovingAverageCrossAPI(name=name, fast_window=fast, slow_window=slow, ma_type=ma_type, mode=IndicatorMode.parse(mode_val))
            case "ATR":
                from Library.Indicator.Technical.Volatility.ATR import AverageTrueRangeAPI
                window = config[1] if len(config) > 1 else 14
                mode_val = config[2] if len(config) > 2 else IndicatorMode.Off
                indicators[name] = AverageTrueRangeAPI(name=name, window=window, mode=IndicatorMode.parse(mode_val))
            case "MACD":
                from Library.Indicator.Technical.Momentum.MACD import MovingAverageConvergenceDivergenceAPI
                slow = config[1] if len(config) > 1 else 26
                fast = config[2] if len(config) > 2 else 12
                signal = config[3] if len(config) > 3 else 9
                mode_val = config[4] if len(config) > 4 else IndicatorMode.Off
                indicators[name] = MovingAverageConvergenceDivergenceAPI(name=name, slow_period=slow, fast_period=fast, signal_period=signal, mode=IndicatorMode.parse(mode_val))
            case _:
                pass
                
    return TechnicalAPI(name="Technical", window=None, mode=IndicatorMode.Off, **indicators)

def parse_fundamental(parameters: Union[dict, None]) -> FundamentalAPI:
    from Library.Indicator.Fundamental.Fundamental import FundamentalAPI
    if not parameters:
        return FundamentalAPI(name="Fundamental", window=None, mode=IndicatorMode.Off)
    indicators = {}
    return FundamentalAPI(name="Fundamental", window=None, mode=IndicatorMode.Off, **indicators)

def parse_sentimental(parameters: Union[dict, None]) -> SentimentalAPI:
    from Library.Indicator.Sentimental.Sentimental import SentimentalAPI
    if not parameters:
        return SentimentalAPI(name="Sentimental", window=None, mode=IndicatorMode.Off)
    indicators = {}
    return SentimentalAPI(name="Sentimental", window=None, mode=IndicatorMode.Off, **indicators)