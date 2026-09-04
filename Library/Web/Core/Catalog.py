from typing import Type

from Library.Strategy import DownloadStrategyAPI, NNFXStrategyAPI, TrendStrategyAPI
from Library.Strategy.Hybrid import DDPGStrategyAPI
from Library.Strategy.Strategy import StrategyAPI

STRATEGIES = (DownloadStrategyAPI, NNFXStrategyAPI, TrendStrategyAPI, DDPGStrategyAPI)
CATALOG = {entry.key(): entry for entry in STRATEGIES}
DEFAULT = TrendStrategyAPI

def resolve(key: str) -> Type[StrategyAPI]:
    return CATALOG.get(key, DEFAULT)