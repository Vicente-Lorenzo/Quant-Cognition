from abc import ABC, abstractmethod

from Library.Database.Dataframe import np

class NormalizerAPI(ABC):
    """
    Generic feature normalizer — the standardization contract for observations.

    An observation encoder emits, per bar, a vector of raw feature values and a
    boolean mask flagging which of them should be standardized (the rest are
    bounded-by-construction and bypass this layer). A concrete normalizer decides
    how the flagged features are standardized (z-score, min-max, running-std, or
    none) and holds whatever running statistics that requires. Implementations must
    be causal — a value is standardized with statistics through the PREVIOUS step
    only — and stateful, hence resettable per episode.
    """

    def reset(self) -> None:
        pass

    @abstractmethod
    def transform(self, values: np.ndarray, mask: np.ndarray) -> np.ndarray:
        raise NotImplementedError