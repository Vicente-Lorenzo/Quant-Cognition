"""
DDPG critic network — the action-value function Q(s, a | theta_Q).

Reference: Lillicrap et al. (2016), "Continuous control with deep reinforcement
learning", arXiv:1509.02971 (Algorithm 1; Section 7 "Experiment Details").

Paper architecture (Section 7, low-dimensional / non-pixel case):
  - Two hidden layers of 400 and 300 units, ReLU activations.
  - "Actions were not included until the 2nd hidden layer of Q": the state is
    processed by the first hidden layer, then the action is merged into the
    second hidden layer. Here the 300-unit state pathway (fc2) and a 300-unit
    action pathway (action_value) are summed and passed through ReLU, then the
    scalar Q head.
  - Hidden layers initialized from U[-1/sqrt(f), 1/sqrt(f)] (f = fan-in); the
    final layer weights AND biases from U[-3e-3, 3e-3] (low-dim case).
  - Adam at a critic learning rate of 1e-3, with L2 weight decay of 1e-2 applied
    to Q only (the actor has no weight decay).

Documented deviation from the paper (normalization):
  - The paper applies batch normalization to the state input and to all layers
    of Q prior to the action input. This module instead applies LayerNorm to the
    two state-pathway pre-activations (none on the raw state input, none after
    the action is merged). See the DDPG actor module docstring for the rationale;
    the layers are named ln* to reflect LayerNorm rather than BatchNorm.
"""

import torch as T
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from pathlib import Path

from Library.Database.Dataframe import np
from Library.Model.Core.Network import NetworkAPI

class CriticNetworkAPI(NetworkAPI):

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

        self.fc1 = nn.Linear(*self.input_shape, self.fc1_shape)
        self.fc2 = nn.Linear(self.fc1_shape, self.fc2_shape)

        self.ln1 = nn.LayerNorm(self.fc1_shape)
        self.ln2 = nn.LayerNorm(self.fc2_shape)

        self.action_value = nn.Linear(self.action_shape, self.fc2_shape)
        self.q = nn.Linear(self.fc2_shape, 1)

        # Section 7: Adam at the critic learning rate (1e-3) with L2 weight decay
        # of 1e-2 applied to Q only.
        self.optimizer = optim.Adam(self.parameters(), lr=beta, weight_decay=0.01)

        self.build()

    def init(self) -> None:
        # Section 7: hidden layers from U[-1/sqrt(f), 1/sqrt(f)], f = fan-in = size()[1].
        f1 = 1. / np.sqrt(self.fc1.weight.data.size()[1])
        self.fc1.weight.data.uniform_(-f1, f1)
        self.fc1.bias.data.uniform_(-f1, f1)
        f2 = 1. / np.sqrt(self.fc2.weight.data.size()[1])
        self.fc2.weight.data.uniform_(-f2, f2)
        self.fc2.bias.data.uniform_(-f2, f2)
        # Section 7: final-layer (Q) weights AND biases from U[-3e-3, 3e-3].
        f3 = 0.003
        self.q.weight.data.uniform_(-f3, f3)
        self.q.bias.data.uniform_(-f3, f3)
        # The action-input layer is treated as a hidden layer (fan-in init).
        f4 = 1. / np.sqrt(self.action_value.weight.data.size()[1])
        self.action_value.weight.data.uniform_(-f4, f4)
        self.action_value.bias.data.uniform_(-f4, f4)

    def forward(self, state, action):
        # State pathway (LayerNorm before ReLU; paper uses BatchNorm here).
        state_value = self.fc1(state)
        state_value = self.ln1(state_value)
        state_value = F.relu(state_value)
        state_value = self.fc2(state_value)
        state_value = self.ln2(state_value)
        # "Actions were not included until the 2nd hidden layer of Q": merge the
        # action pathway into the 300-unit state pathway, then ReLU, then Q head.
        action_value = self.action_value(action)
        state_action_value = F.relu(T.add(state_value, action_value))
        state_action_value = self.q(state_action_value)
        return state_action_value