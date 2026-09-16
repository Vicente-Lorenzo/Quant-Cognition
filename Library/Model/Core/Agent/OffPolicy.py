import torch as T
from typing import Union
from pathlib import Path

from Library.Database.Dataframe import np
from Library.Model.Core.Agent.Agent import AgentAPI
from Library.Model.Core.Memory import MemoryAPI

class OffPolicyAgentAPI(AgentAPI):

    def __init__(self, model: str, path: Path, input_shape: tuple, action_shape: int, memory_size: int, seed: Union[int, None] = None):
        super().__init__(model=model, path=path)
        if seed is not None:
            T.manual_seed(seed)
        self.memory = MemoryAPI(size=memory_size, input_shape=input_shape, action_shape=action_shape, seed=seed)

    @staticmethod
    def _soft_update_(source, target, tau) -> None:
        with T.no_grad():
            for online, target_param in zip(source.parameters(), target.parameters()):
                target_param.copy_(tau * online + (1.0 - tau) * target_param)

    def memorize(self, state, action, reward, next_state, done) -> None:
        self.memory.memorize(state, action, reward, next_state, done)

    def remember(self, batch_size) -> (np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray):
        return self.memory.remember(batch_size)