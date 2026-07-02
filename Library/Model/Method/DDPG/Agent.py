"""
DDPG agent — Deep Deterministic Policy Gradient (off-policy, actor-critic).

Reference: Lillicrap, Hunt, Pritzel, Heess, Erez, Tassa, Silver, Wierstra (2016),
"Continuous control with deep reinforcement learning", arXiv:1509.02971.
This module implements Algorithm 1 ("DDPG algorithm") with the Section 7
hyperparameters. Notation below mirrors the paper.

Components: an online actor mu(s|theta_mu) and critic Q(s,a|theta_Q), their target
networks mu' and Q', a replay buffer R (MemoryAPI), and an Ornstein-Uhlenbeck
exploration process N (OrnsteinUhlenbeckNoiseAPI).

Default hyperparameters (Section 7, low-dimensional case):
  - alpha (actor lr) = 1e-4 · beta (critic lr) = 1e-3 (Adam).
  - tau = 1e-3 (soft target update) · gamma = 0.99.
  - replay buffer = 1e6 · minibatch N = 64.
  - fc1 = 400 · fc2 = 300.
  - L2 weight decay 1e-2 on Q only (set in CriticNetworkAPI).
  - OU exploration: theta = 0.15, sigma = 0.2, mu = 0 (passed below).

Reference-implementation conventions (not specified by the paper):
  - The OU process discretization step dt = 1e-2 (the paper gives only the
    continuous process); this is the OrnsteinUhlenbeckNoiseAPI default.
  - Terminal masking V(terminal) = 0 in the critic target (standard episodic
    handling; Algorithm 1 is written for the continuing case).
"""

import torch as T
import torch.nn.functional as F
from typing import Union
from pathlib import Path

from Library.Database.Dataframe import np
from Library.Model.Core.Agent import AgentAPI
from Library.Model.Core.Memory import MemoryAPI
from Library.Model.Core.Noise import OrnsteinUhlenbeckNoiseAPI
from Library.Model.Method.DDPG import ActorNetworkAPI, CriticNetworkAPI

class DDPGAgentAPI(AgentAPI):

    def __init__(self,
                 path: Path,
                 input_shape: tuple,
                 action_shape: int,
                 alpha: float = 0.0001,
                 beta: float = 0.001,
                 tau: float = 0.001,
                 fc1_shape: int = 400,
                 fc2_shape: int = 300,
                 memory_size: int = 1000000,
                 batch_size: int = 64,
                 gamma: float = 0.99,
                 grad_clip: float = 1.0,
                 seed: Union[int, None] = None):

        super().__init__(model="DDPG", path=path)

        if seed is not None:
            T.manual_seed(seed)

        self.batch_size = batch_size
        self.gamma = gamma
        self.tau = tau
        self.grad_clip = grad_clip

        self.memory = MemoryAPI(size=memory_size, input_shape=input_shape, action_shape=action_shape, seed=seed)

        # Ornstein-Uhlenbeck exploration N (Section 7): theta = 0.15 (mean
        # reversion), sigma = 0.2 (volatility), mu = 0 ("centered around 0").
        self.noise = OrnsteinUhlenbeckNoiseAPI(mu=np.zeros(action_shape), sigma=0.2, theta=0.15, seed=seed)

        self.actor = ActorNetworkAPI(
            model=self._model,
            role="actor",
            path=path,
            input_shape=input_shape,
            action_shape=action_shape,
            fc1_shape=fc1_shape,
            fc2_shape=fc2_shape,
            alpha=alpha
        )

        self.target_actor = ActorNetworkAPI(
            model=self._model,
            role="target_actor",
            path=path,
            input_shape=input_shape,
            action_shape=action_shape,
            fc1_shape=fc1_shape,
            fc2_shape=fc2_shape,
            alpha=alpha
        )

        self.critic = CriticNetworkAPI(
            model=self._model,
            role="critic",
            path=path,
            input_shape=input_shape,
            action_shape=action_shape,
            fc1_shape=fc1_shape,
            fc2_shape=fc2_shape,
            beta=beta
        )

        self.target_critic = CriticNetworkAPI(
            model=self._model,
            role="target_critic",
            path=path,
            input_shape=input_shape,
            action_shape=action_shape,
            fc1_shape=fc1_shape,
            fc2_shape=fc2_shape,
            beta=beta
        )

        # Initialize the targets equal to the online networks (Algorithm 1):
        # theta_Q' <- theta_Q and theta_mu' <- theta_mu (a hard copy, tau = 1).
        self.update(force_tau=1)

    def save(self) -> None:
        self.actor.save()
        self.target_actor.save()
        self.critic.save()
        self.target_critic.save()
        super().save()

    def load(self) -> None:
        self.actor.load()
        self.target_actor.load()
        self.critic.load()
        self.target_critic.load()
        super().load()

    def reset(self) -> None:
        # Reset the OU process state between episodes (it is temporally correlated).
        self.noise.reset()

    def memorize(self, state, action, reward, next_state, done) -> None:
        self.memory.memorize(state, action, reward, next_state, done)

    def remember(self, batch_size) -> (np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray):
        return self.memory.remember(batch_size)

    def decide(self, state, explore: bool = True):
        # Algorithm 1: a_t = mu(s_t | theta_mu) + N_t, then bound to [-1, 1].
        # eval()/train() bracket the forward pass; with LayerNorm this is a no-op
        # (no batch statistics) but is kept so a BatchNorm swap stays correct.
        self.actor.eval()
        with T.no_grad():
            state = T.as_tensor(np.asarray(state, dtype=np.float32), device=self.actor.device).unsqueeze(0)
            mu = self.actor.forward(state)
            if explore:
                mu = mu + T.tensor(self.noise(), dtype=T.float).to(self.actor.device)
            mu = T.clamp(mu, -1.0, 1.0)
        self.actor.train()
        return mu.cpu().numpy()[0]

    def update(self, force_tau=None):
        # Soft target update (Algorithm 1): theta' <- tau*theta + (1-tau)*theta'.
        # force_tau=1 performs the hard copy used to initialize the targets.
        # Applied in place (no clone/state-dict round-trip) for speed; the
        # arithmetic is identical to tau*theta + (1-tau)*theta'.
        tau = force_tau if force_tau is not None else self.tau
        self._soft_update_(self.critic, self.target_critic, tau)
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

        # Sample a random minibatch of N transitions from R (Algorithm 1).
        states, actions, rewards, next_states, dones = self.remember(self.batch_size)

        states = T.tensor(states, dtype=T.float).to(self.actor.device)
        actions = T.tensor(actions, dtype=T.float).to(self.actor.device)
        rewards = T.tensor(rewards, dtype=T.float).to(self.actor.device)
        next_states = T.tensor(next_states, dtype=T.float).to(self.actor.device)
        dones = T.tensor(dones).to(self.actor.device)

        # Critic target using the TARGET actor and TARGET critic (no gradient):
        #   y_i = r_i + gamma * Q'(s_{i+1}, mu'(s_{i+1})).
        # Terminal next-states contribute 0 (V(terminal) = 0).
        with T.no_grad():
            target_next_actions = self.target_actor.forward(next_states)
            target_next_state_action_value = self.target_critic.forward(next_states, target_next_actions)
            target_next_state_action_value[dones] = 0.0
            target_next_state_action_value = target_next_state_action_value.view(-1)
            target_state_action_value = rewards + self.gamma*target_next_state_action_value
            target_state_action_value = target_state_action_value.view(self.batch_size, 1)

        # Critic update: minimize L = (1/N) sum_i (y_i - Q(s_i, a_i))^2 (Algorithm 1).
        state_action_value = self.critic.forward(states, actions)

        self.critic.optimizer.zero_grad()
        critic_loss = F.mse_loss(target_state_action_value, state_action_value)
        critic_loss.backward()
        # Gradient-norm clipping (not in the paper): a standard optimization
        # stabilizer that bounds the per-step update. It does not alter the DDPG
        # objective or Algorithm 1; it prevents the actor's final layer from being
        # slammed into tanh saturation (dead gradient -> constant-action collapse).
        if self.grad_clip > 0.0:
            T.nn.utils.clip_grad_norm_(self.critic.parameters(), self.grad_clip)
        self.critic.optimizer.step()

        # Actor update via the deterministic policy gradient (Algorithm 1):
        #   grad_theta_mu J ~= (1/N) sum_i grad_a Q(s,a)|_{a=mu(s_i)} grad_theta_mu mu(s_i).
        # Realized as ascent on Q(s, mu(s)), i.e. descent on -mean Q(s, mu(s)).
        # The critic parameters are frozen for this backward pass (gradients still
        # flow THROUGH the critic to the actor); this only skips accumulating
        # critic parameter gradients that the next zero_grad would discard, so the
        # actor update is numerically identical (standard reference-impl practice).
        for parameter in self.critic.parameters(): parameter.requires_grad_(False)
        self.actor.optimizer.zero_grad()
        actor_loss = -self.critic.forward(states, self.actor.forward(states))
        actor_loss = T.mean(actor_loss)
        actor_loss.backward()
        if self.grad_clip > 0.0:
            T.nn.utils.clip_grad_norm_(self.actor.parameters(), self.grad_clip)
        self.actor.optimizer.step()
        for parameter in self.critic.parameters(): parameter.requires_grad_(True)

        # Soft-update both target networks (Algorithm 1).
        self.update()