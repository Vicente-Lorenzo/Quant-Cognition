from __future__ import annotations

from typing import TYPE_CHECKING

from Library.Strategy.Model.Model import ModelStrategyAPI

if TYPE_CHECKING:
    from Library.Model.Core.Agent import AgentAPI

class DDPGStrategyAPI(ModelStrategyAPI):

    def _create_agent_(self, observation_shape: tuple, action_shape: int) -> AgentAPI:
        from Library.Model import DDPGAgentAPI
        return DDPGAgentAPI(
            path=self._weights_path_(),
            input_shape=observation_shape,
            action_shape=action_shape,
            alpha=self._value_(self.SignalManagement, "ActorLearningRate", 0.0001),
            beta=self._value_(self.SignalManagement, "CriticLearningRate", 0.001),
            tau=self._value_(self.SignalManagement, "SoftUpdate", 0.001),
            fc1_shape=self._value_(self.SignalManagement, "HiddenShape1", 400),
            fc2_shape=self._value_(self.SignalManagement, "HiddenShape2", 300),
            memory_size=self._value_(self.SignalManagement, "MemorySize", 1000000),
            batch_size=self._value_(self.SignalManagement, "BatchSize", 64),
            gamma=self._value_(self.SignalManagement, "DiscountFactor", 0.99),
            grad_clip=self._value_(self.SignalManagement, "GradientClip", 1.0),
            seed=self.Seed
        )