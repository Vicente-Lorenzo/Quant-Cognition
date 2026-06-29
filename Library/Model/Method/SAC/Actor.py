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

        self.mu = nn.Linear(self.fc2_shape, self.action_shape)
        self.log_std = nn.Linear(self.fc2_shape, self.action_shape)

        self.optimizer = optim.Adam(self.parameters(), lr=learning_rate)

        self.build()

    def init(self) -> None:
        f1 = 1. / np.sqrt(self.fc1.weight.data.size()[1])
        self.fc1.weight.data.uniform_(-f1, f1)
        self.fc1.bias.data.uniform_(-f1, f1)

        f2 = 1. / np.sqrt(self.fc2.weight.data.size()[1])
        self.fc2.weight.data.uniform_(-f2, f2)
        self.fc2.bias.data.uniform_(-f2, f2)

        f3 = 0.003
        self.mu.weight.data.uniform_(-f3, f3)
        self.mu.bias.data.uniform_(-f3, f3)
        self.log_std.weight.data.uniform_(-f3, f3)
        self.log_std.bias.data.uniform_(-f3, f3)

    def forward(self, state):
        probability = F.relu(self.fc1(state))
        probability = F.relu(self.fc2(probability))
        mu = self.mu(probability)
        log_std = T.clamp(self.log_std(probability), self._LOG_STD_MIN_, self._LOG_STD_MAX_)
        return mu, log_std

    def sample(self, state):
        mu, log_std = self.forward(state)
        distribution = T.distributions.Normal(mu, log_std.exp())
        sample = distribution.rsample()
        action = T.tanh(sample)
        log_probability = distribution.log_prob(sample) - T.log(1.0 - action.pow(2) + self._EPSILON_)
        log_probability = log_probability.sum(dim=-1, keepdim=True)
        return action, log_probability
