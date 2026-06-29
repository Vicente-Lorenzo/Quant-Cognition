import torch as T
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from pathlib import Path

from Library.Database.Dataframe import np
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

        self.fc1 = nn.Linear(self.input_shape[0] + self.action_shape, self.fc1_shape)
        self.fc2 = nn.Linear(self.fc1_shape, self.fc2_shape)

        self.q = nn.Linear(self.fc2_shape, 1)

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
        self.q.weight.data.uniform_(-f3, f3)
        self.q.bias.data.uniform_(-f3, f3)

    def forward(self, state, action):
        action_value = T.cat([state, action], dim=-1)
        action_value = F.relu(self.fc1(action_value))
        action_value = F.relu(self.fc2(action_value))
        return self.q(action_value)
