from Library.Strategy.Strategy import StrategyAPI
from Library.Strategy.Rule.NNFX import NNFXStrategyAPI
from Library.Strategy.Rule.Trend import TrendStrategyAPI
from Library.Strategy.Rule.Test import TestStrategyAPI
from Library.Strategy.Hybrid.DDPG import DDPGStrategyAPI

class CatalogAPI:

    STRATEGIES: tuple[type[StrategyAPI], ...] = (NNFXStrategyAPI, TrendStrategyAPI, TestStrategyAPI, DDPGStrategyAPI)
    CATALOG: dict[str, type[StrategyAPI]] = {entry.key(): entry for entry in STRATEGIES}
    DEFAULT: type[StrategyAPI] = TrendStrategyAPI

    @classmethod
    def resolve(cls, key: str) -> type[StrategyAPI]:
        return cls.CATALOG.get(key, cls.DEFAULT)