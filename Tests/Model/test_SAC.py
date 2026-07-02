import numpy as np
import torch as T

from Library.Model import SACAgentAPI

def _agent_(path, seed=42, state_dim=4, action_dim=1, batch_size=8, memory_size=200):
    return SACAgentAPI(path=path, input_shape=(state_dim,), action_shape=action_dim, batch_size=batch_size, memory_size=memory_size, seed=seed)

def _fill_(agent, n, state_dim=4, action_dim=1):
    rng = np.random.default_rng(0)
    for _ in range(n):
        agent.memorize(rng.normal(size=state_dim), rng.uniform(-1.0, 1.0, size=action_dim), rng.normal(), rng.normal(size=state_dim), False)

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

def test_explore_is_stochastic(tmp_path):
    agent = _agent_(tmp_path)
    state = np.linspace(-1.0, 1.0, 4)
    samples = np.array([agent.decide(state, explore=True) for _ in range(16)])
    assert samples.std() > 0.0

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
    before = agent.critic_1.fc1.weight.detach().clone()
    agent.learn()
    assert T.equal(before, agent.critic_1.fc1.weight.detach())

def test_learn_updates_parameters_and_temperature(tmp_path):
    agent = _agent_(tmp_path, batch_size=8, memory_size=200)
    _fill_(agent, 32)
    critic_before = agent.critic_1.fc1.weight.detach().clone()
    alpha_before = agent.log_alpha.detach().clone()
    agent.learn()
    assert not T.allclose(critic_before, agent.critic_1.fc1.weight.detach())
    assert not T.allclose(alpha_before, agent.log_alpha.detach())

def test_target_critics_track_online(tmp_path):
    agent = _agent_(tmp_path, batch_size=8, memory_size=200)
    _fill_(agent, 32)
    target_before = agent.target_critic_1.fc1.weight.detach().clone()
    for _ in range(5):
        agent.learn()
    assert not T.allclose(target_before, agent.target_critic_1.fc1.weight.detach())

def test_memorize_and_remember_shapes(tmp_path):
    agent = _agent_(tmp_path, batch_size=8, memory_size=200)
    _fill_(agent, 20)
    states, actions, rewards, next_states, dones = agent.remember(8)
    assert states.shape == (8, 4)
    assert actions.shape == (8, 1)
    assert rewards.shape == (8,)
    assert next_states.shape == (8, 4)
    assert dones.shape == (8,)

def test_save_load_roundtrip(tmp_path):
    state = np.linspace(-1.0, 1.0, 4)
    source = _agent_(tmp_path, seed=1)
    source.save()
    target = _agent_(tmp_path, seed=2)
    target.load()
    assert np.allclose(source.decide(state, explore=False), target.decide(state, explore=False))
    assert np.allclose(source.log_alpha.detach().cpu().numpy(), target.log_alpha.detach().cpu().numpy())