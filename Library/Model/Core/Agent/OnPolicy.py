import torch as T
from typing import Union
from pathlib import Path

from Library.Database.Dataframe import np
from Library.Model.Core.Agent.Agent import AgentAPI
from Library.Model.Core.Memory import RolloutAPI
from Library.Utility.Typing import MISSING

class OnPolicyAgentAPI(AgentAPI):

    def __init__(self, model: str, path: Path, input_shape: tuple, action_shape: int, seed: Union[int, None] = None):
        super().__init__(model=model, path=path)
        if seed is not None:
            T.manual_seed(seed)
        self.rollout = RolloutAPI(input_shape=input_shape, action_shape=action_shape)

    def forget(self) -> None:
        self.rollout.forget()

    def memorize(self, state, action, reward, next_state, done) -> None:
        self.rollout.memorize(state, action, reward, next_state, done)

    def remember(self, batch_size: int = MISSING) -> (np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray):
        return self.rollout.remember(batch_size)