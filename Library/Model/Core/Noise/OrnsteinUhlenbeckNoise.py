from typing import Union

from Library.Database.Dataframe import np
from Library.Model.Core.Noise import NoiseAPI

class OrnsteinUhlenbeckNoiseAPI(NoiseAPI):
    """
    Ornstein-Uhlenbeck Noise (Mean-Reverting Stochastic Process)

    Characteristics:
    - Distribution: Normal
    - Memory: Yes (stateful)
    - Stationary: Yes (in long run)
    - Markov: Yes
    - Bounded: No (but reverts toward mean)
    - Domain: ℝ (real numbers)

    This noise model generates temporally correlated values using an OU process,
    which tends to revert toward a long-term mean `mu` with a strength controlled
    by `theta`. The volatility of the random fluctuations is governed by `sigma`,
    and `dt` defines the timestep. Commonly used in reinforcement learning for
    exploration noise.
    """

    def __init__(self,
                 mu: Union[np.ndarray, float],
                 sigma: float = 0.2,
                 theta: float = 0.15,
                 dt: float = 1.0,
                 x0: Union[np.ndarray, float, None] = None,
                 seed: Union[float, None] = None):
        super().__init__(seed)
        self._mu: Union[np.ndarray, float] = mu
        self._sigma: float = sigma
        self._theta: float = theta
        self._dt: float = dt
        self._x0: Union[np.ndarray, float, None] = x0
        self._x_prev: Union[np.ndarray, float, None] = None
        self.reset()

    def __call__(self) -> Union[np.ndarray, float]:
        noise = self._theta * (self._mu - self._x_prev) * self._dt + self._sigma * np.sqrt(self._dt) * self._sample_()
        self._x_prev += noise
        return self._x_prev

    def reset(self) -> None:
        self._x_prev = self._origin_(self._x0, self._mu, np.zeros_like)