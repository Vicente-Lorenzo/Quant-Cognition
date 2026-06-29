from typing import Union

from Library.Database.Dataframe import np
from Library.Model.Core.Noise import NoiseAPI

class BrownianNoiseAPI(NoiseAPI):
    """
    Brownian Motion (Wiener Process)

    Characteristics:
    - Distribution: Normal increments
    - Memory: Yes (stateful)
    - Stationary: No
    - Markov: Yes
    - Bounded: No
    - Domain: ℝ (real numbers)

    This noise model simulates Brownian motion (Wiener process), where each
    output is the cumulative sum of small Gaussian perturbations. It models
    continuous-time stochastic processes with drift `mu`, volatility `sigma`,
    and time step `dt`. The initial state is defined by `x0` (default 0).
    """

    def __init__(self,
                 mu: Union[np.ndarray, float],
                 sigma: float = 0.15,
                 dt: float = 1e-2,
                 x0: Union[np.ndarray, float, None] = None,
                 seed: Union[int, None] = None):
        super().__init__(seed)
        self._mu: Union[np.ndarray, float] = mu
        self._sigma: float = sigma
        self._dt: float = dt
        self._x0: Union[np.ndarray, float, None] = x0
        self._x_prev: Union[np.ndarray, float, None] = None
        self.reset()

    def __call__(self) -> Union[np.ndarray, float]:
        if np.isscalar(self._mu):
            noise = self._mu * self._dt + self._sigma * np.sqrt(self._dt) * self._rng.normal()
        else:
            noise = self._mu * self._dt + self._sigma * np.sqrt(self._dt) * self._rng.normal(size=self._mu.shape)
        self._x_prev += noise
        return self._x_prev

    def reset(self) -> None:
        if self._x0 is not None:
            self._x_prev = np.copy(self._x0)
        else:
            self._x_prev = np.zeros_like(self._mu)
