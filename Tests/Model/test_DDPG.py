import numpy as np
import torch as T

from Library.Model import DDPGAgentAPI

def _agent_(path, seed=42, state_dim=4, action_dim=1, batch_size=8, memory_size=100):
    return DDPGAgentAPI(path=path, input_shape=(state_dim,), action_shape=action_dim, batch_size=batch_size, memory_size=memory_size, seed=seed)

def _fill_(agent, n, state_dim=4, action_dim=1):
    rng = np.random.default_rng(0)
    for _ in range(n):
        agent.memorise(rng.normal(size=state_dim), rng.uniform(-1.0, 1.0, size=action_dim), rng.normal(), rng.normal(size=state_dim), False)

def test_decide_is_bounded(tmp_path):
    agent = _agent_(tmp_path)
    state = np.zeros(4)
    for _ in range(50):
        action = agent.decide(state, explore=True)
        assert action.shape == (1,)
        assert np.all(action >= -1.0) and np.all(action <= 1.0)

def test_decide_greedy_is_deterministic(tmp_path):
    agent = _agent_(tmp_path)
    state = np.linspace(-1.0, 1.0, 4)
    assert np.allclose(agent.decide(state, explore=False), agent.decide(state, explore=False))

def test_same_seed_reproduces_policy(tmp_path):
    state = np.linspace(-1.0, 1.0, 4)
    first = _agent_(tmp_path, seed=123).decide(state, explore=False)
    second = _agent_(tmp_path, seed=123).decide(state, explore=False)
    assert np.allclose(first, second)

def test_different_seeds_differ(tmp_path):
    state = np.linspace(-1.0, 1.0, 4)
    first = _agent_(tmp_path, seed=1).decide(state, explore=False)
    second = _agent_(tmp_path, seed=2).decide(state, explore=False)
    assert not np.allclose(first, second)

def test_learn_warmup_guard_does_not_crash(tmp_path):
    agent = _agent_(tmp_path)
    before = agent.critic.fc1.weight.detach().clone()
    agent.learn()
    assert T.equal(before, agent.critic.fc1.weight.detach())

def test_learn_updates_parameters(tmp_path):
    agent = _agent_(tmp_path, batch_size=8, memory_size=100)
    _fill_(agent, 32)
    before = agent.critic.fc1.weight.detach().clone()
    agent.learn()
    assert not T.allclose(before, agent.critic.fc1.weight.detach())

def test_memorise_and_remember_shapes(tmp_path):
    agent = _agent_(tmp_path, memory_size=100)
    _fill_(agent, 10)
    states, actions, rewards, next_states, dones = agent.remember(5)
    assert states.shape == (5, 4)
    assert actions.shape == (5, 1)
    assert rewards.shape == (5,)
    assert next_states.shape == (5, 4)
    assert dones.shape == (5,)

def test_save_load_roundtrip(tmp_path):
    state = np.linspace(-1.0, 1.0, 4)
    source = _agent_(tmp_path, seed=1)
    source.save()
    target = _agent_(tmp_path, seed=2)
    target.load()
    assert np.allclose(source.decide(state, explore=False), target.decide(state, explore=False))
