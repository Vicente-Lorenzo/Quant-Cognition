from typing import Union
from pathlib import Path
from abc import ABC, abstractmethod

from Library.Database.Dataframe import np
from Library.Logging import LoggingAPI

class AgentAPI(ABC):

    def __init__(self, model: str, path: Path):
        super().__init__()
        self._model = model
        self._path = path
        self._log: LoggingAPI = LoggingAPI("Agent Management")

    @abstractmethod
    def save(self) -> None:
        self._log.debug(lambda: f"Saved agent state for {self._model}")

    @abstractmethod
    def load(self) -> None:
        self._log.debug(lambda: f"Loaded agent state for {self._model}")

    @abstractmethod
    def reset(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def memorize(self, state, action, reward, next_state, done) -> None:
        raise NotImplementedError

    @abstractmethod
    def remember(self, batch_size) -> (np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray):
        raise NotImplementedError

    @abstractmethod
    def decide(self, state, explore: bool = True) -> Union[np.ndarray, float, int]:
        raise NotImplementedError

    @abstractmethod
    def update(self, *args) -> None:
        raise NotImplementedError

    @abstractmethod
    def learn(self) -> None:
        raise NotImplementedError