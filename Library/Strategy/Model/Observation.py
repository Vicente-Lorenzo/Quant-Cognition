from __future__ import annotations

from abc import ABC, abstractmethod
from collections import deque
from typing import TYPE_CHECKING

from Library.Database.Dataframe import np
from Library.Strategy.Model.Normalizer import NormalizerAPI

if TYPE_CHECKING:
    from Library.Protocol.Update import BarUpdateAPI

class ObservationAPI(ABC):
    """
    Generic observation encoder — turns a per-bar update into a fixed-length
    float32 vector, with pluggable normalization and optional frame stacking.

    Subclasses define the feature design by implementing _features_ (the ordered
    (value, standardize) pairs for one bar) and _frame_size_ (the per-bar feature
    count). The standardize flag routes a feature through the normalizer; features
    that are bounded by construction pass it as False to bypass that layer.

    The base owns the shared, strategy-agnostic machinery: normalization via a
    NormalizerAPI, a rolling window of the last `window` frames (oldest -> newest,
    repeat-padded on the first bar so the shape is constant from step one), and
    reset. Encoders are stateful and must be reset per episode; subclasses that
    carry their own running state override _reset_state_.
    """

    def __init__(self, normalizer: NormalizerAPI, window: int) -> None:
        self._normalizer_ = normalizer
        self._window_ = max(1, window)
        self._frames_: deque = deque(maxlen=self._window_)

    def reset(self) -> None:
        self._normalizer_.reset()
        self._frames_.clear()
        self._reset_state_()

    def shape(self) -> int:
        return self._window_ * self._frame_size_()

    def _reset_state_(self) -> None:
        pass

    @abstractmethod
    def _frame_size_(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def _features_(self, update: BarUpdateAPI) -> list:
        raise NotImplementedError

    def encode(self, update: BarUpdateAPI) -> np.ndarray:
        features = self._features_(update)
        values = np.array([value for value, _ in features], dtype=np.float32)
        mask = np.array([flag for _, flag in features], dtype=bool)
        frame = self._normalizer_.transform(values, mask)
        if self._window_ == 1: return frame
        if not self._frames_:
            for _ in range(self._window_): self._frames_.append(frame)
        else:
            self._frames_.append(frame)
        return np.concatenate(self._frames_)