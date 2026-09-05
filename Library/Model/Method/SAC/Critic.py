"""
SAC soft critic network — a soft action-value function Q(s, a | theta).

Reference: Haarnoja et al. (2018), "Soft Actor-Critic Algorithms and
Applications", arXiv:1812.05905 (v2). SAC v2 uses TWO independent soft Q-networks
(clipped double-Q) plus their targets to mitigate positive bias; this class
defines a single soft Q-network and the SACAgentAPI instantiates it four times
(critic_1, critic_2, target_critic_1, target_critic_2).

Architecture (v2 Appendix D, Table 1): the state and action are concatenated at
the input (unlike DDPG, which injects the action at the 2nd layer), followed by
two hidden layers of 256 units with ReLU and a scalar Q head.

Reference-implementation convention (NOT specified by the paper):
  - Weight initialization: PyTorch default nn.Linear init (Kaiming-uniform),
    matching SpinningUp / CleanRL.
"""

import torch as T
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from pathlib import Path

from Library.Model.Core.Network import NetworkAPI

class SoftCriticNetworkAPI(NetworkAPI):

    def __init__(self,
                 model: str,
                 role: str,
                 path: Path,
                 input_shape: tuple,
                 action_shape: int,
                 fc1_shape: int,
                 fc2_shape: int,
                 learning_rate: float):

        super().__init__(model=model, role=role, path=path)

        self.input_shape = input_shape
        self.action_shape = action_shape
        self.fc1_shape = fc1_shape
        self.fc2_shape = fc2_shape

        # Q(s, a): state and action concatenated at the input layer.
        self.fc1 = nn.Linear(self.input_shape[0] + self.action_shape, self.fc1_shape)
        self.fc2 = nn.Linear(self.fc1_shape, self.fc2_shape)

        self.q = nn.Linear(self.fc2_shape, 1)

        self.optimizer = optim.Adam(self.parameters(), lr=learning_rate)

        self.build()

    def init(self) -> None:
        # The SAC papers do not prescribe a weight initialization. We keep
        # PyTorch's default nn.Linear init (Kaiming-uniform), matching the
        # SpinningUp / CleanRL SAC references. This hook is intentionally a no-op.
        pass

    def forward(self, state, action):
        action_value = T.cat([state, action], dim=-1)
        action_value = F.relu(self.fc1(action_value))
        action_value = F.relu(self.fc2(action_value))
        return self.q(action_value)