"""
TD3 critic network — one action-value function Q(s, a | theta_Q) of the twin pair.

Reference: Fujimoto, van Hoof, Meger (2018), "Addressing Function Approximation
Error in Actor-Critic Methods", arXiv:1802.09477 (ICML 2018). TD3 maintains TWO
independent critics (Clipped Double Q-learning, Section 4.2) plus their targets;
this class defines a single critic and the TD3AgentAPI instantiates it four times
(critic_1, critic_2, target_critic_1, target_critic_2).

Paper architecture (Section 6.1 / Supplementary Material):
  - The state and action are concatenated at the input layer (unlike the DDPG
    paper, which injects the action at the 2nd hidden layer).
  - Two hidden layers of 400 and 300 units, ReLU activations, scalar Q head.
  - Optimized with Adam at a learning rate of 1e-3, no L2 weight decay (TD3
    drops DDPG's critic weight decay).
  - No normalization layers.

Reference-implementation convention (NOT specified by the paper):
  - Weight initialization: PyTorch default nn.Linear init (Kaiming-uniform),
    matching the official author implementation (sfujim/TD3).
"""

import torch as T
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from pathlib import Path

from Library.Model.Core.Network import NetworkAPI

class TD3CriticNetworkAPI(NetworkAPI):

    def __init__(self,
                 model: str,
                 role: str,
                 path: Path,
                 input_shape: tuple,
                 action_shape: int,
                 fc1_shape: int,
                 fc2_shape: int,
                 beta: float):

        super().__init__(model=model, role=role, path=path)

        self.input_shape = input_shape
        self.action_shape = action_shape
        self.fc1_shape = fc1_shape
        self.fc2_shape = fc2_shape

        # Q(s, a): state and action concatenated at the input layer.
        self.fc1 = nn.Linear(self.input_shape[0] + self.action_shape, self.fc1_shape)
        self.fc2 = nn.Linear(self.fc1_shape, self.fc2_shape)

        self.q = nn.Linear(self.fc2_shape, 1)

        self.optimizer = optim.Adam(self.parameters(), lr=beta)

        self.build()

    def init(self) -> None:
        # The paper does not prescribe a weight initialization. We keep PyTorch's
        # default nn.Linear init (Kaiming-uniform), matching the official
        # implementation (sfujim/TD3). This hook is intentionally a no-op.
        pass

    def forward(self, state, action):
        action_value = T.cat([state, action], dim=-1)
        action_value = F.relu(self.fc1(action_value))
        action_value = F.relu(self.fc2(action_value))
        return self.q(action_value)