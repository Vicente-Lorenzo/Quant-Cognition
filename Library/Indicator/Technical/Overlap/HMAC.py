from Library.Indicator.Indicator import IndicatorMode
from Library.Indicator.Technical.Overlap.MAC import MovingAverageCrossAPI
from Library.Indicator.Technical.Technical import TechnicalAPI
from Library.Indicator.Technical.Baseline.MA import MovingAverageType

class HullMovingAverageCrossAPI(MovingAverageCrossAPI):

    Parameters = (TechnicalAPI.FAST, TechnicalAPI.SLOW, TechnicalAPI.MODE)

    def __init__(self, name: str, fast_window: int, slow_window: int, mode: IndicatorMode) -> None:
        super().__init__(name=name, fast_window=fast_window, slow_window=slow_window, type=MovingAverageType.Hull, mode=mode)