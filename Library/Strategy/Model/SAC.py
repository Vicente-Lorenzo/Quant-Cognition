from __future__ import annotations

from typing import TYPE_CHECKING

from Library.Strategy.Model.Model import ModelStrategyAPI

if TYPE_CHECKING:
    from Library.Model.Core.Agent import AgentAPI

class SACStrategyAPI(ModelStrategyAPI):

    def _create_agent_(self, observation_shape: tuple, action_shape: int) -> AgentAPI:
        from Library.Model import SACAgentAPI
        return SACAgentAPI(
            path=self._weights_path_(),
            input_shape=observation_shape,
            action_shape=action_shape,
            actor_lr=self._value_(self.SignalManagement, "ActorLearningRate", 0.0003),
            critic_lr=self._value_(self.SignalManagement, "CriticLearningRate", 0.0003),
            temperature_lr=self._value_(self.SignalManagement, "TemperatureLearningRate", 0.0003),
            tau=self._value_(self.SignalManagement, "SoftUpdate", 0.005),
            fc1_shape=self._value_(self.SignalManagement, "HiddenShape1", 256),
            fc2_shape=self._value_(self.SignalManagement, "HiddenShape2", 256),
            memory_size=self._value_(self.SignalManagement, "MemorySize", 1000000),
            batch_size=self._value_(self.SignalManagement, "BatchSize", 256),
            gamma=self._value_(self.SignalManagement, "DiscountFactor", 0.99),
            target_entropy=self._value_(self.SignalManagement, "TargetEntropy", None),
            seed=self.Seed
        )