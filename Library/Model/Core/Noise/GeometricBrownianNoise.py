from typing import Union

from Library.Database.Dataframe import np
from Library.Model.Core.Noise import NoiseAPI

class GeometricBrownianNoiseAPI(NoiseAPI):
    """
    Geometric Brownian Motion (Log-Normal Process)

    Characteristics:
    - Distribution: Log-normal
    - Memory: Yes (stateful)
    - Stationary: No
    - Markov: Yes
    - Bounded: No (but always positive)
    - Domain: ℝ⁺ (positive real numbers)

    This noise model simulates a stochastic process where each value is a
    multiplicative update based on Brownian motion. It is often used to model
    stock prices, where the returns are normally distributed but the process
    itself is log-normally distributed. Initial value is `s0` (default 1).
    """

    def __init__(self,
                 mu: Union[np.ndarray, float],
                 sigma: float = 0.15,
                 dt: float = 1e-2,
                 s0: Union[np.ndarray, float, None] = None,
                 seed: Union[int, None] = None):
        super().__init__(seed)
        self._mu: Union[np.ndarray, float] = mu
        self._sigma: float = sigma
        self._dt: float = dt
        self._s0: Union[np.ndarray, float, None] = s0
        self._s_prev: Union[np.ndarray, float, None] = None
        self.reset()

    def __call__(self) -> Union[np.ndarray, float]:
        if np.isscalar(self._mu):
            noise = self._rng.normal()
            drift = (self._mu - 0.5 * self._sigma ** 2) * self._dt
            diffusion = self._sigma * np.sqrt(self._dt) * noise
        else:
            noise = self._rng.normal(size=self._mu.shape)
            drift = (self._mu - 0.5 * self._sigma ** 2) * self._dt
            diffusion = self._sigma * np.sqrt(self._dt) * noise

        self._s_prev *= np.exp(drift + diffusion)
        return self._s_prev

    def reset(self) -> None:
        if self._s0 is not None:
            self._s_prev = np.copy(self._s0)
        else:
            self._s_prev = np.ones_like(self._mu)