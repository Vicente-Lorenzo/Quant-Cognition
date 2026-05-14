import torch as T
import torch.nn as nn
from pathlib import Path
from abc import ABC, abstractmethod

from Library.Logging import HandlerLoggingAPI

class NetworkAPI(nn.Module, ABC):

    def __init__(self, model: str, role: str, path: Path):
        super().__init__()
        self._model = model
        self._role = role

        self._path = path
        self._file = path / model / role
        self._log: HandlerLoggingAPI = HandlerLoggingAPI(Class=self.__class__.__name__, Subclass="Network Management")

        self.init()
        self.device = T.device("cuda:0" if T.cuda.is_available() else "cuda:1")
        self.to(self.device)

    @abstractmethod
    def init(self) -> None:
        raise NotImplementedError

    def save(self) -> None:
        T.save(self.state_dict(), str(self._file))
        self._log.debug(lambda: f"Saved network state for {self._model} {self._role}")

    def load(self) -> None:
        self.load_state_dict(T.load(str(self._file)))
        self._log.debug(lambda: f"Loaded network state for {self._model} {self._role}")
