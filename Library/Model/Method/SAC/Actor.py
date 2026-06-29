"""
SAC actor network — the squashed-Gaussian stochastic policy pi(a | s).

Reference: Haarnoja, Zhou, Hartikainen, Tucker, Ha, Tan, Kumar, Zhu, Gupta,
Abbeel, Levine (2018), "Soft Actor-Critic Algorithms and Applications",
arXiv:1812.05905 (the v2 / automatic-temperature formulation). The squashing and
log-probability correction are from the original SAC paper, Haarnoja et al.
(2018), arXiv:1801.01290, Appendix C "Enforcing Action Bounds".

Policy: the network outputs a state-dependent Gaussian (mean mu and log-std);
an action is drawn by the reparameterization trick and squashed through tanh:
  a = tanh( mu(s) + sigma(s) * eps ),   eps ~ N(0, I)            (v2 Eq. 8)
The tanh change of variables gives the bounded-action log-likelihood:
  log pi(a|s) = log mu_N(u|s) - sum_i log(1 - tanh^2(u_i))       (v1 Eq. 21)
where u is the pre-squash Gaussian sample.

Architecture (v2 Appendix D, Table 1): two hidden layers of 256 units, ReLU.

Reference-implementation conventions (NOT specified by either paper):
  - log-std clamp to [-20, 2] for numerical stability (softlearning / rlkit /
    SpinningUp).
  - +1e-6 epsilon inside the log(1 - tanh^2) correction to avoid log(0)
    (softlearning / rlkit).
  - Weight initialization: PyTorch default nn.Linear init (Kaiming-uniform),
    matching SpinningUp / CleanRL; the papers prescribe no initialization.
"""

import torch as T
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from pathlib import Path

from Library.Database.Dataframe import np
from Library.Model.Core.Network import NetworkAPI

class GaussianActorNetworkAPI(NetworkAPI):

    _LOG_STD_MIN_ = -20.0
    _LOG_STD_MAX_ = 2.0
    _EPSILON_ = 1e-6

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

        self.fc1 = nn.Linear(*self.input_shape, self.fc1_shape)
        self.fc2 = nn.Linear(self.fc1_shape, self.fc2_shape)

        # Separate heads for the Gaussian mean and log standard deviation.
        self.mu = nn.Linear(self.fc2_shape, self.action_shape)
        self.log_std = nn.Linear(self.fc2_shape, self.action_shape)

        self.optimizer = optim.Adam(self.parameters(), lr=learning_rate)

        self.build()

    def init(self) -> None:
        # The SAC papers do not prescribe a weight initialization. We keep
        # PyTorch's default nn.Linear init (Kaiming-uniform), matching the
        # SpinningUp / CleanRL SAC references. This hook is intentionally a no-op.
        pass

    def forward(self, state):
        probability = F.relu(self.fc1(state))
        probability = F.relu(self.fc2(probability))
        mu = self.mu(probability)
        # Clamp log-std for stability (reference-impl convention, not the paper).
        log_std = T.clamp(self.log_std(probability), self._LOG_STD_MIN_, self._LOG_STD_MAX_)
        return mu, log_std

    def sample(self, state):
        mu, log_std = self.forward(state)
        # Reparameterized sample u = mu + sigma * eps, eps ~ N(0, I) (v2 Eq. 8);
        # rsample() keeps the path differentiable for the policy gradient.
        distribution = T.distributions.Normal(mu, log_std.exp())
        sample = distribution.rsample()
        # Squash into (-1, 1): a = tanh(u).
        action = T.tanh(sample)
        # tanh change-of-variables correction (v1 Eq. 21); +epsilon avoids log(0).
        log_probability = distribution.log_prob(sample) - T.log(1.0 - action.pow(2) + self._EPSILON_)
        # Sum over action dimensions -> scalar log-density per sample.
        log_probability = log_probability.sum(dim=-1, keepdim=True)
        return action, log_probability