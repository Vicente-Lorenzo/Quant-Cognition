import numpy as np
import torch as T

from Library.Model import OnPolicyAgentAPI, RolloutAPI

class _AgentAPI_(OnPolicyAgentAPI):

    def save(self) -> None:
        super().save()

    def load(self) -> None:
        super().load()

    def reset(self) -> None:
        pass

    def decide(self, state, explore: bool = True):
        return np.zeros(self.rollout.action_shape)

    def update(self, *args) -> None:
        pass

    def learn(self) -> None:
        self.forget()

def _agent_(path, seed=7):
    return _AgentAPI_(model="Rollout", path=path, input_shape=(3,), action_shape=2, seed=seed)

def _fill_(agent, n):
    for step in range(n):
        agent.memorize(np.full(3, step), np.full(2, -step), float(step), np.full(3, step + 1), step == n - 1)

def test_remember_returns_the_rollout_in_order(tmp_path):
    agent = _agent_(tmp_path)
    _fill_(agent, 4)
    states, actions, rewards, next_states, dones = agent.remember()
    assert states.shape == (4, 3) and actions.shape == (4, 2) and next_states.shape == (4, 3)
    assert rewards.tolist() == [0.0, 1.0, 2.0, 3.0]
    assert dones.tolist() == [False, False, False, True]
    assert states[:, 0].tolist() == [0.0, 1.0, 2.0, 3.0]

def test_remember_with_a_size_keeps_the_most_recent_steps(tmp_path):
    agent = _agent_(tmp_path)
    _fill_(agent, 5)
    states, _, rewards, _, _ = agent.remember(2)
    assert rewards.tolist() == [3.0, 4.0]
    assert states.shape == (2, 3)

def test_forget_empties_the_rollout_but_keeps_the_count(tmp_path):
    agent = _agent_(tmp_path)
    _fill_(agent, 3)
    agent.learn()
    states, actions, rewards, next_states, dones = agent.remember()
    assert states.shape == (0, 3) and actions.shape == (0, 2) and rewards.size == 0 and dones.size == 0
    assert agent.rollout.counter == 3

def test_a_seed_makes_torch_reproducible(tmp_path):
    _agent_(tmp_path, seed=11)
    first = T.rand(3)
    _agent_(tmp_path, seed=11)
    assert T.equal(first, T.rand(3))

def test_rollout_is_exported_beside_the_replay_memory():
    assert RolloutAPI(input_shape=(1,), action_shape=1).remember()[0].shape == (0, 1)