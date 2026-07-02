"""
SAC agent — Soft Actor-Critic (off-policy, maximum-entropy actor-critic).

Reference: Haarnoja, Zhou, Hartikainen, Tucker, Ha, Tan, Kumar, Zhu, Gupta,
Abbeel, Levine (2018), "Soft Actor-Critic Algorithms and Applications",
arXiv:1812.05905 (the v2 formulation). This module implements the v2 practical
algorithm: a squashed-Gaussian policy, TWIN soft Q-functions with clipped
double-Q targets, target Q-networks (no separate value network), and an
AUTOMATICALLY tuned entropy temperature alpha.

Per-step updates (v2):
  - Critic target (Section 6), with a' ~ pi(.|s'):
        y = r + gamma * ( min_{i=1,2} Q_target_i(s', a') - alpha * log pi(a'|s') )
    Each online critic regresses to y: J_Q = E[ 0.5 (Q_i(s,a) - y)^2 ].
  - Actor (reparameterized) ascends the entropy-regularized value:
        J_pi = E[ alpha * log pi(a|s) - min_{i=1,2} Q_i(s, a) ],  a ~ pi(.|s).
  - Temperature (v2 Eq. 18) with target entropy H_bar = -dim(A) (Table 1):
        J(alpha) = E[ -alpha * log pi(a|s) - alpha * H_bar ].
  - Soft target update: theta_target_i <- tau*theta_i + (1-tau)*theta_target_i.

Default hyperparameters (v2 Appendix D, Table 1):
  - learning rate 3e-4 (Adam) for actor, critics, and temperature.
  - gamma = 0.99 · tau = 0.005 · batch = 256 · replay = 1e6.
  - fc1 = fc2 = 256 · target update interval = 1 (every gradient step).
  - target entropy H_bar = -dim(A).

Reference-implementation conventions (NOT specified by the paper):
  - The temperature is parameterized and optimized as log_alpha = log(alpha) for
    positivity/stability; the paper's Algorithm 1 writes the update on alpha.
  - log-std clamp [-20, 2], the +1e-6 tanh-correction epsilon, and the default
    weight initialization (see the SAC actor/critic modules).
"""

import torch as T
import torch.nn.functional as F
import torch.optim as optim
from typing import Union
from pathlib import Path

from Library.Database.Dataframe import np
from Library.Model.Core.Agent import AgentAPI
from Library.Model.Core.Memory import MemoryAPI
from Library.Model.Method.SAC import GaussianActorNetworkAPI, SoftCriticNetworkAPI

class SACAgentAPI(AgentAPI):

    def __init__(self,
                 path: Path,
                 input_shape: tuple,
                 action_shape: int,
                 actor_lr: float = 0.0003,
                 critic_lr: float = 0.0003,
                 temperature_lr: float = 0.0003,
                 tau: float = 0.005,
                 fc1_shape: int = 256,
                 fc2_shape: int = 256,
                 memory_size: int = 1000000,
                 batch_size: int = 256,
                 gamma: float = 0.99,
                 target_entropy: Union[float, None] = None,
                 seed: Union[int, None] = None):

        super().__init__(model="SAC", path=path)

        if seed is not None:
            T.manual_seed(seed)

        self.batch_size = batch_size
        self.gamma = gamma
        self.tau = tau

        self.memory = MemoryAPI(size=memory_size, input_shape=input_shape, action_shape=action_shape, seed=seed)

        self.actor = GaussianActorNetworkAPI(model=self._model, role="actor", path=path, input_shape=input_shape, action_shape=action_shape, fc1_shape=fc1_shape, fc2_shape=fc2_shape, learning_rate=actor_lr)

        # Twin soft Q-functions (clipped double-Q) and their target networks.
        self.critic_1 = SoftCriticNetworkAPI(model=self._model, role="critic_1", path=path, input_shape=input_shape, action_shape=action_shape, fc1_shape=fc1_shape, fc2_shape=fc2_shape, learning_rate=critic_lr)
        self.critic_2 = SoftCriticNetworkAPI(model=self._model, role="critic_2", path=path, input_shape=input_shape, action_shape=action_shape, fc1_shape=fc1_shape, fc2_shape=fc2_shape, learning_rate=critic_lr)

        self.target_critic_1 = SoftCriticNetworkAPI(model=self._model, role="target_critic_1", path=path, input_shape=input_shape, action_shape=action_shape, fc1_shape=fc1_shape, fc2_shape=fc2_shape, learning_rate=critic_lr)
        self.target_critic_2 = SoftCriticNetworkAPI(model=self._model, role="target_critic_2", path=path, input_shape=input_shape, action_shape=action_shape, fc1_shape=fc1_shape, fc2_shape=fc2_shape, learning_rate=critic_lr)

        # Automatic temperature: target entropy H_bar = -dim(A) (Table 1), and a
        # learnable log_alpha (alpha = exp(log_alpha)) optimized via J(alpha).
        self.target_entropy = float(-action_shape) if target_entropy is None else float(target_entropy)
        self.log_alpha = T.zeros(1, requires_grad=True, device=self.actor.device)
        self.alpha = self.log_alpha.exp()
        self.alpha_optimizer = optim.Adam([self.log_alpha], lr=temperature_lr)

        # Initialize the target critics equal to the online critics (hard copy).
        self.update(force_tau=1)

    def save(self) -> None:
        self.actor.save()
        self.critic_1.save()
        self.critic_2.save()
        self.target_critic_1.save()
        self.target_critic_2.save()
        file = self._path / self._model / "log_alpha"
        file.parent.mkdir(parents=True, exist_ok=True)
        T.save(self.log_alpha.detach().cpu(), str(file))
        super().save()

    def load(self) -> None:
        self.actor.load()
        self.critic_1.load()
        self.critic_2.load()
        self.target_critic_1.load()
        self.target_critic_2.load()
        loaded = T.load(str(self._path / self._model / "log_alpha"), weights_only=True).to(self.actor.device)
        with T.no_grad():
            self.log_alpha.copy_(loaded)
        self.alpha = self.log_alpha.exp()
        super().load()

    def reset(self) -> None:
        # SAC explores intrinsically through its stochastic policy; there is no
        # external noise process to reset between episodes.
        pass

    def memorize(self, state, action, reward, next_state, done) -> None:
        self.memory.memorize(state, action, reward, next_state, done)

    def remember(self, batch_size) -> (np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray):
        return self.memory.remember(batch_size)

    def decide(self, state, explore: bool = True):
        # explore=True samples from pi (training); explore=False returns the
        # deterministic mean action tanh(mu) for evaluation/greedy rollouts.
        self.actor.eval()
        with T.no_grad():
            state = T.as_tensor(np.asarray(state, dtype=np.float32), device=self.actor.device).unsqueeze(0)
            if explore:
                action, _ = self.actor.sample(state)
            else:
                mu, _ = self.actor.forward(state)
                action = T.tanh(mu)
        self.actor.train()
        return action.cpu().numpy()[0]

    def update(self, force_tau=None) -> None:
        # Soft target update: theta_target_i <- tau*theta_i + (1-tau)*theta_target_i.
        # force_tau=1 performs the hard copy used to initialize the targets.
        tau = force_tau if force_tau is not None else self.tau
        self._soft_update_(self.critic_1, self.target_critic_1, tau)
        self._soft_update_(self.critic_2, self.target_critic_2, tau)

    @staticmethod
    def _soft_update_(source, target, tau) -> None:
        with T.no_grad():
            for online, target_param in zip(source.parameters(), target.parameters()):
                target_param.copy_(tau * online + (1.0 - tau) * target_param)

    def learn(self) -> None:
        # Wait until the replay buffer holds at least one full minibatch.
        if self.memory.counter < self.batch_size:
            return

        states, actions, rewards, next_states, dones = self.remember(self.batch_size)

        device = self.actor.device
        states = T.as_tensor(states, dtype=T.float, device=device)
        actions = T.as_tensor(actions, dtype=T.float, device=device)
        rewards = T.as_tensor(rewards, dtype=T.float, device=device).view(-1, 1)
        next_states = T.as_tensor(next_states, dtype=T.float, device=device)
        dones = T.as_tensor(dones, dtype=T.float, device=device).view(-1, 1)

        # Critic target (no gradient): sample next actions from the CURRENT policy,
        # take the minimum over the two TARGET critics (clipped double-Q), subtract
        # the entropy term, and bootstrap:
        #   y = r + gamma * (1 - done) * ( min_i Q_target_i(s', a') - alpha log pi(a'|s') ).
        with T.no_grad():
            next_actions, next_log_probabilities = self.actor.sample(next_states)
            target_value = T.min(self.target_critic_1.forward(next_states, next_actions), self.target_critic_2.forward(next_states, next_actions)) - self.alpha * next_log_probabilities
            target = rewards + self.gamma * (1.0 - dones) * target_value

        # Critic update: each online critic regresses its Q(s, a) onto y.
        critic_loss = F.mse_loss(self.critic_1.forward(states, actions), target) + F.mse_loss(self.critic_2.forward(states, actions), target)
        self.critic_1.optimizer.zero_grad()
        self.critic_2.optimizer.zero_grad()
        critic_loss.backward()
        self.critic_1.optimizer.step()
        self.critic_2.optimizer.step()

        # Actor update (reparameterized): minimize alpha*log pi(a|s) - min_i Q_i(s, a)
        # with a ~ pi(.|s). alpha is detached so the actor does not move it.
        # Both critics' parameters are frozen for this backward pass (gradients
        # still flow THROUGH them to the actor); this only skips accumulating
        # critic parameter gradients that the next zero_grad would discard, so the
        # actor update is numerically identical (standard reference-impl practice).
        for parameter in self.critic_1.parameters(): parameter.requires_grad_(False)
        for parameter in self.critic_2.parameters(): parameter.requires_grad_(False)
        new_actions, log_probabilities = self.actor.sample(states)
        value = T.min(self.critic_1.forward(states, new_actions), self.critic_2.forward(states, new_actions))
        actor_loss = (self.alpha.detach() * log_probabilities - value).mean()
        self.actor.optimizer.zero_grad()
        actor_loss.backward()
        self.actor.optimizer.step()
        for parameter in self.critic_1.parameters(): parameter.requires_grad_(True)
        for parameter in self.critic_2.parameters(): parameter.requires_grad_(True)

        # Temperature update (v2 Eq. 18): minimize -log_alpha*(log pi(a|s) + H_bar);
        # log pi is detached (alpha adapts to the policy, not vice versa).
        alpha_loss = -(self.log_alpha * (log_probabilities + self.target_entropy).detach()).mean()
        self.alpha_optimizer.zero_grad()
        alpha_loss.backward()
        self.alpha_optimizer.step()
        self.alpha = self.log_alpha.exp()

        # Soft-update both target critics every gradient step (Table 1: interval 1).
        self.update()