from typing import Union
from abc import ABC, abstractmethod

from Library.Database.Dataframe import np

class NoiseAPI(ABC):

    def __init__(self,
                 seed: Union[int, None] = None):
        self._rng = np.random.default_rng(seed)

    @staticmethod
    def _origin_(start: Union[np.ndarray, float, None], mu: Union[np.ndarray, float], fill) -> Union[np.ndarray, float]:
        return np.copy(start) if start is not None else fill(mu)

    def _sample_(self) -> Union[np.ndarray, float]:
        return self._rng.normal() if np.isscalar(self._mu) else self._rng.normal(size=self._mu.shape)

    @abstractmethod
    def __call__(self) -> np.ndarray:
        pass

    @abstractmethod
    def reset(self) -> None:
        pass