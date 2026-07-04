"""
DDPG actor network — the deterministic policy mu(s | theta_mu).

Reference: Lillicrap, Hunt, Pritzel, Heess, Erez, Tassa, Silver, Wierstra (2016),
"Continuous control with deep reinforcement learning", arXiv:1509.02971
(Algorithm 1; architecture and hyperparameters in Section 7 "Experiment Details").

Paper architecture (Section 7, low-dimensional / non-pixel case):
  - Two hidden layers of 400 and 300 units, ReLU activations.
  - Final layer is a tanh that bounds the action to [-1, 1].
  - Hidden layers initialized from U[-1/sqrt(f), 1/sqrt(f)] with f the fan-in;
    the final layer weights AND biases from U[-3e-3, 3e-3] (low-dim case).
  - Optimized with Adam at an actor learning rate of 1e-4.

Documented deviation from the paper (normalization):
  - The paper applies batch normalization to the state input and to every layer
    of the actor. This module instead applies LayerNorm to the two hidden
    pre-activations and none to the raw state input. This follows the Phil Tabor
    reference implementation (https://www.youtube.com/watch?v=4jh32CvwKYw).
    Rationale: LayerNorm normalizes per sample, so single-sample action selection
    (batch size 1) and minibatch training behave identically; this avoids the
    BatchNorm running-statistic and target-network pitfalls of the original and
    is a widely used, more stable substitution. The layers are named ln* (not the
    paper's bn*) to reflect that they are LayerNorm, not BatchNorm.
"""

import torch as T
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from pathlib import Path

from Library.Database.Dataframe import np
from Library.Model.Core.Network import NetworkAPI

class ActorNetworkAPI(NetworkAPI):

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

        self.ln1 = nn.LayerNorm(self.fc1_shape)
        self.ln2 = nn.LayerNorm(self.fc2_shape)

        self.mu = nn.Linear(self.fc2_shape, self.action_shape)

        self.optimizer = optim.Adam(self.parameters(), lr=alpha)

        self.build()

    def init(self) -> None:
        # Section 7: hidden layers from U[-1/sqrt(f), 1/sqrt(f)], f = fan-in.
        # For an nn.Linear weight of shape (out, in), fan-in is size()[1].
        f1 = 1. / np.sqrt(self.fc1.weight.data.size()[1])
        self.fc1.weight.data.uniform_(-f1, f1)
        self.fc1.bias.data.uniform_(-f1, f1)
        f2 = 1. / np.sqrt(self.fc2.weight.data.size()[1])
        self.fc2.weight.data.uniform_(-f2, f2)
        self.fc2.bias.data.uniform_(-f2, f2)
        # Section 7: final-layer weights AND biases from U[-3e-3, 3e-3] (low-dim).
        f3 = 0.003
        self.mu.weight.data.uniform_(-f3, f3)
        self.mu.bias.data.uniform_(-f3, f3)

    def preactivation(self, state):
        # The pre-tanh activation u(s) = mu_linear( fc2( fc1(s) ) ) with LayerNorm
        # before each ReLU. Exposed separately so the Extended DDPG variant can
        # regularize u directly; forward() is exactly tanh(preactivation).
        action = self.fc1(state)
        action = self.ln1(action)
        action = F.relu(action)
        action = self.fc2(action)
        action = self.ln2(action)
        action = F.relu(action)
        return self.mu(action)

    def forward(self, state):
        # mu(s) = tanh( u(s) ) (paper uses BatchNorm in u; see module docstring).
        # Final tanh bounds the deterministic action to [-1, 1] (Section 7).
        return T.tanh(self.preactivation(state))