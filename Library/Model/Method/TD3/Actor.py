"""
TD3 actor network — the deterministic policy pi(s | theta_pi).

Reference: Fujimoto, van Hoof, Meger (2018), "Addressing Function Approximation
Error in Actor-Critic Methods", arXiv:1802.09477 (ICML 2018). Architecture and
hyperparameters from Section 6.1 and the Supplementary Material.

Paper architecture:
  - Two hidden layers of 400 and 300 units, ReLU activations.
  - Final layer is a tanh that bounds the action to [-1, 1].
  - Optimized with Adam at a learning rate of 1e-3.
  - No normalization layers (unlike DDPG's batch normalization, which TD3 drops).

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

class TD3ActorNetworkAPI(NetworkAPI):

    def __init__(self,
                 model: str,
                 role: str,
                 path: Path,
                 input_shape: tuple,
                 action_shape: int,
                 fc1_shape: int,
                 fc2_shape: int,
                 alpha: float):

        super().__init__(model=model, role=role, path=path)

        self.input_shape = input_shape
        self.action_shape = action_shape
        self.fc1_shape = fc1_shape
        self.fc2_shape = fc2_shape

        self.fc1 = nn.Linear(*self.input_shape, self.fc1_shape)
        self.fc2 = nn.Linear(self.fc1_shape, self.fc2_shape)

        self.mu = nn.Linear(self.fc2_shape, self.action_shape)

        self.optimizer = optim.Adam(self.parameters(), lr=alpha)

        self.build()

    def init(self) -> None:
        # The paper does not prescribe a weight initialization. We keep PyTorch's
        # default nn.Linear init (Kaiming-uniform), matching the official
        # implementation (sfujim/TD3). This hook is intentionally a no-op.
        pass

    def forward(self, state):
        # pi(s) = tanh( fc2( fc1(s) ) ) — plain ReLU MLP, no normalization.
        action = F.relu(self.fc1(state))
        action = F.relu(self.fc2(action))
        # Final tanh bounds the deterministic action to [-1, 1].
        return T.tanh(self.mu(action))