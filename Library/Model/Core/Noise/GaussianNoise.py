from typing import Union

from Library.Database.Dataframe import np
from Library.Model.Core.Noise import NoiseAPI

class GaussianNoiseAPI(NoiseAPI):
    """
    Gaussian White Noise

    Characteristics:
    - Distribution: Normal
    - Memory: No
    - Stationary: Yes
    - Markov: Yes
    - Bounded: No
    - Domain: ℝ (real numbers)

    This noise model generates i.i.d. samples from a normal distribution
    with mean `mu` and standard deviation `sigma`. It is typically used
    to simulate purely random (white) noise in continuous domains.
    """

    def __init__(self,
                 mu: Union[np.ndarray, float],
                 sigma: float = 0.15,
                 seed: Union[int, None] = None):
        super().__init__(seed)
        self._mu: Union[np.ndarray, float] = mu
        self._sigma: float = sigma

    def __call__(self) -> Union[np.ndarray, float]:
        if np.isscalar(self._mu):
            return self._mu + self._sigma * self._rng.normal()
        else:
            return self._mu + self._sigma * self._rng.normal(size=self._mu.shape)

    def reset(self) -> None:
        pass
