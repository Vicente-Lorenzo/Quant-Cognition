"""
TD3 agent — Twin Delayed Deep Deterministic Policy Gradient (off-policy,
actor-critic).

Reference: Fujimoto, van Hoof, Meger (2018), "Addressing Function Approximation
Error in Actor-Critic Methods", arXiv:1802.09477 (ICML 2018). This module
implements Algorithm 1 ("TD3") with the Section 6.1 / Supplementary Material
hyperparameters. Notation below mirrors the paper.

TD3 = DDPG + three fixes for critic overestimation and variance:
  1. Clipped Double Q-learning (Section 4.2): two critics Q_1, Q_2; the target
     uses the MINIMUM of the two target critics.
  2. Target policy smoothing (Section 5.3): the target action is the target
     policy's output plus clipped Gaussian noise,
         a~ = pi'(s') + epsilon,  epsilon ~ clip(N(0, sigma~), -c, c),
     which regularizes the value estimate over a small area around the action.
  3. Delayed policy updates (Section 5.2): the actor and ALL target networks
     update only every d critic updates.

Per-step updates (Algorithm 1):
  - Critic target (both critics regress to the same y):
        y = r + gamma * min_{i=1,2} Q'_i(s', pi'(s') + epsilon).
    Terminal next-states contribute 0 (standard episodic masking).
  - Every d steps: actor ascends Q_1(s, pi(s)) (deterministic policy gradient
    on the FIRST critic only), then all targets soft-update:
        theta' <- tau*theta + (1-tau)*theta'.

Default hyperparameters (Section 6.1 / Supplementary Material):
  - Adam learning rate 1e-3 for actor and critics.
  - gamma = 0.99 · tau = 0.005 · batch N = 100 · replay buffer = 1e6.
  - fc1 = 400 · fc2 = 300 (ReLU; no normalization, no weight decay).
  - Exploration noise: epsilon ~ N(0, 0.1) added to each action.
  - Target policy smoothing: sigma~ = 0.2, clip c = 0.5 · policy delay d = 2.

Reference-implementation conventions (NOT specified by Algorithm 1):
  - Terminal masking V(terminal) = 0 in the critic target.
  - The paper's MuJoCo protocol uses a purely random policy for the first 1e4
    steps; that is an evaluation-protocol detail outside Algorithm 1 and is not
    used here (exploration noise applies from the first step, consistent with
    this framework's DDPG).
"""

import torch as T
import torch.nn.functional as F
from typing import Union
from pathlib import Path

from Library.Database.Dataframe import np
from Library.Model.Core.Agent import AgentAPI
from Library.Model.Core.Memory import MemoryAPI
from Library.Model.Core.Noise import GaussianNoiseAPI
from Library.Model.Method.TD3 import TD3ActorNetworkAPI, TD3CriticNetworkAPI

class TD3AgentAPI(AgentAPI):

    def __init__(self,
                 path: Path,
                 input_shape: tuple,
                 action_shape: int,
                 alpha: float = 0.001,
                 beta: float = 0.001,
                 tau: float = 0.005,
                 fc1_shape: int = 400,
                 fc2_shape: int = 300,
                 memory_size: int = 1000000,
                 batch_size: int = 100,
                 gamma: float = 0.99,
                 exploration_noise: float = 0.1,
                 policy_noise: float = 0.2,
                 noise_clip: float = 0.5,
                 policy_delay: int = 2,
                 seed: Union[int, None] = None):

        super().__init__(model="TD3", path=path)

        if seed is not None:
            T.manual_seed(seed)

        self.batch_size = batch_size
        self.gamma = gamma
        self.tau = tau
        self.policy_noise = policy_noise
        self.noise_clip = noise_clip
        self.policy_delay = policy_delay
        self.learn_counter = 0

        self.memory = MemoryAPI(size=memory_size, input_shape=input_shape, action_shape=action_shape, seed=seed)

        # Gaussian exploration noise epsilon ~ N(0, 0.1) added to each action
        # (Section 6.1; TD3 replaces DDPG's OU process with uncorrelated noise).
        self.noise = GaussianNoiseAPI(mu=np.zeros(action_shape), sigma=exploration_noise, seed=seed)

        self.actor = TD3ActorNetworkAPI(model=self._model, role="actor", path=path, input_shape=input_shape, action_shape=action_shape, fc1_shape=fc1_shape, fc2_shape=fc2_shape, alpha=alpha)
        self.target_actor = TD3ActorNetworkAPI(model=self._model, role="target_actor", path=path, input_shape=input_shape, action_shape=action_shape, fc1_shape=fc1_shape, fc2_shape=fc2_shape, alpha=alpha)

        # Twin critics (Clipped Double Q-learning) and their target networks.
        self.critic_1 = TD3CriticNetworkAPI(model=self._model, role="critic_1", path=path, input_shape=input_shape, action_shape=action_shape, fc1_shape=fc1_shape, fc2_shape=fc2_shape, beta=beta)
        self.critic_2 = TD3CriticNetworkAPI(model=self._model, role="critic_2", path=path, input_shape=input_shape, action_shape=action_shape, fc1_shape=fc1_shape, fc2_shape=fc2_shape, beta=beta)
        self.target_critic_1 = TD3CriticNetworkAPI(model=self._model, role="target_critic_1", path=path, input_shape=input_shape, action_shape=action_shape, fc1_shape=fc1_shape, fc2_shape=fc2_shape, beta=beta)
        self.target_critic_2 = TD3CriticNetworkAPI(model=self._model, role="target_critic_2", path=path, input_shape=input_shape, action_shape=action_shape, fc1_shape=fc1_shape, fc2_shape=fc2_shape, beta=beta)

        # Initialize the targets equal to the online networks (Algorithm 1):
        # theta' <- theta and phi' <- phi (a hard copy, tau = 1).
        self.update(force_tau=1)

    def save(self) -> None:
        self.actor.save()
        self.target_actor.save()
        self.critic_1.save()
        self.critic_2.save()
        self.target_critic_1.save()
        self.target_critic_2.save()
        super().save()

    def load(self) -> None:
        self.actor.load()
        self.target_actor.load()
        self.critic_1.load()
        self.critic_2.load()
        self.target_critic_1.load()
        self.target_critic_2.load()
        super().load()

    def reset(self) -> None:
        # Gaussian exploration noise is memoryless; nothing to reset between
        # episodes (kept for interface symmetry with the OU-based DDPG).
        self.noise.reset()

    def memorize(self, state, action, reward, next_state, done) -> None:
        self.memory.memorize(state, action, reward, next_state, done)

    def remember(self, batch_size) -> (np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray):
        return self.memory.remember(batch_size)

    def decide(self, state, explore: bool = True):
        # Algorithm 1: a = pi(s) + epsilon, epsilon ~ N(0, sigma), bounded to [-1, 1].
        self.actor.eval()
        with T.no_grad():
            state = T.as_tensor(np.asarray(state, dtype=np.float32), device=self.actor.device).unsqueeze(0)
            mu = self.actor.forward(state)
            if explore:
                mu = mu + T.tensor(self.noise(), dtype=T.float).to(self.actor.device)
            mu = T.clamp(mu, -1.0, 1.0)
        self.actor.train()
        return mu.cpu().numpy()[0]

    def update(self, force_tau=None) -> None:
        # Soft target update (Algorithm 1): theta' <- tau*theta + (1-tau)*theta'.
        # force_tau=1 performs the hard copy used to initialize the targets.
        tau = force_tau if force_tau is not None else self.tau
        self._soft_update_(self.critic_1, self.target_critic_1, tau)
        self._soft_update_(self.critic_2, self.target_critic_2, tau)
        self._soft_update_(self.actor, self.target_actor, tau)

    @staticmethod
    def _soft_update_(source, target, tau) -> None:
        with T.no_grad():
            for online, target_param in zip(source.parameters(), target.parameters()):
                target_param.copy_(tau * online + (1.0 - tau) * target_param)

    def learn(self) -> None:
        # Wait until the replay buffer holds at least one full minibatch.
        if self.memory.counter < self.batch_size:
            return

        # Sample a random minibatch of N transitions (Algorithm 1).
        states, actions, rewards, next_states, dones = self.remember(self.batch_size)

        device = self.actor.device
        states = T.as_tensor(states, dtype=T.float, device=device)
        actions = T.as_tensor(actions, dtype=T.float, device=device)
        rewards = T.as_tensor(rewards, dtype=T.float, device=device).view(-1, 1)
        next_states = T.as_tensor(next_states, dtype=T.float, device=device)
        dones = T.as_tensor(dones, dtype=T.float, device=device).view(-1, 1)

        # Critic target (no gradient) with target policy smoothing (Algorithm 1):
        #   a~ = pi'(s') + epsilon, epsilon ~ clip(N(0, sigma~), -c, c), a~ in [-1, 1];
        #   y = r + gamma * min_{i=1,2} Q'_i(s', a~).
        # Terminal next-states contribute 0 (V(terminal) = 0).
        with T.no_grad():
            smoothing = (T.randn_like(actions) * self.policy_noise).clamp(-self.noise_clip, self.noise_clip)
            next_actions = (self.target_actor.forward(next_states) + smoothing).clamp(-1.0, 1.0)
            target_value = T.min(self.target_critic_1.forward(next_states, next_actions), self.target_critic_2.forward(next_states, next_actions))
            target = rewards + self.gamma * (1.0 - dones) * target_value

        # Critic update: both critics regress to the SAME clipped target y,
        #   L = N^-1 sum (y - Q_i(s, a))^2 for i = 1, 2 (Algorithm 1).
        critic_loss = F.mse_loss(self.critic_1.forward(states, actions), target) + F.mse_loss(self.critic_2.forward(states, actions), target)
        self.critic_1.optimizer.zero_grad()
        self.critic_2.optimizer.zero_grad()
        critic_loss.backward()
        self.critic_1.optimizer.step()
        self.critic_2.optimizer.step()

        # Delayed policy updates (Algorithm 1): the actor and ALL target networks
        # update only every d critic updates.
        self.learn_counter += 1
        if self.learn_counter % self.policy_delay != 0:
            return

        # Actor update via the deterministic policy gradient on Q_1 only:
        #   grad J = N^-1 sum grad_a Q_1(s, a)|_{a=pi(s)} grad_phi pi(s).
        # Realized as descent on -mean Q_1(s, pi(s)). The critic parameters are
        # frozen for this backward pass (gradients still flow THROUGH the critic
        # to the actor); this only skips accumulating critic parameter gradients
        # that the next zero_grad would discard, so the actor update is
        # numerically identical (standard reference-impl practice).
        for parameter in self.critic_1.parameters(): parameter.requires_grad_(False)
        self.actor.optimizer.zero_grad()
        actor_loss = -T.mean(self.critic_1.forward(states, self.actor.forward(states)))
        actor_loss.backward()
        self.actor.optimizer.step()
        for parameter in self.critic_1.parameters(): parameter.requires_grad_(True)

        # Soft-update the target actor and both target critics (Algorithm 1).
        self.update()