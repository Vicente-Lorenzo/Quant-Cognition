from typing import Union
from abc import ABC, abstractmethod

from Library.Database.Dataframe import np

class NoiseAPI(ABC):

    def __init__(self,
                 seed: Union[int, None] = None):
        self._rng = np.random.default_rng(seed)

    @abstractmethod
    def __call__(self) -> np.ndarray:
        pass

    @abstractmethod
    def reset(self) -> None:
        pass