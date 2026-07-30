import torch as T
import torch.nn as nn
from pathlib import Path
from abc import ABC, abstractmethod

from Library.Logging import LoggingAPI

class NetworkAPI(nn.Module, ABC):

    def __init__(self, model: str, role: str, path: Path):
        super().__init__()
        self._model = model
        self._role = role

        self._path = path
        self._file = path / model / role
        self._log: LoggingAPI = LoggingAPI("Network Management")

    @abstractmethod
    def init(self) -> None:
        raise NotImplementedError

    def build(self) -> None:
        self.init()
        self.device = T.device("cuda:0" if T.cuda.is_available() else "cpu")
        self.to(self.device)

    def save(self) -> None:
        self._file.parent.mkdir(parents=True, exist_ok=True)
        T.save(self.state_dict(), str(self._file))
        self._log.debug(lambda: f"Saved network state for {self._model} {self._role}")

    def load(self) -> None:
        self.load_state_dict(T.load(str(self._file), map_location=self.device, weights_only=True))
        self._log.debug(lambda: f"Loaded network state for {self._model} {self._role}")