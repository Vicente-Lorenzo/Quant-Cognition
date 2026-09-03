import json
import sys
import time
from typing import Union
from typing_extensions import Self

from Library.Utility.Datetime import seconds_to_clock

class ProgressAPI:

    SENTINEL: str = "~progress~"
    _MUTED_: bool = False
    _WIDTH_: int = 28
    _ALPHA_: float = 0.2
    _INTERVAL_: float = 0.25
    _FRACTION_: float = 0.01

    def __init__(self, total: int, *, label: Union[str, None] = None, unit: str = "step",
                 interval: Union[float, None] = None, fraction: Union[float, None] = None) -> None:
        self._total_ = max(0, int(total or 0))
        self._label_ = label
        self._unit_ = unit
        self._interval_ = self._INTERVAL_ if interval is None else interval
        self._stride_ = max(1, int(self._total_ * (self._FRACTION_ if fraction is None else fraction)))
        self._position_ = 0
        self._threshold_ = self._stride_
        self._started_ = time.monotonic()
        self._stamp_ = self._started_
        self._anchor_ = 0
        self._pace_: Union[float, None] = None
        self._closed_ = False
        self._bar_ = not self._MUTED_ and self._attached_(sys.stderr)
        self._wire_ = not self._MUTED_ and not self._attached_(sys.stdout)

    def __enter__(self) -> Self:
        self._render_(force=True)
        return self

    def __exit__(self, *error) -> None:
        self.close()

    @classmethod
    def mute(cls, muted: bool = True) -> None:
        cls._MUTED_ = muted

    @staticmethod
    def _attached_(stream) -> bool:
        try: return bool(stream) and stream.isatty()
        except Exception: return False

    @property
    def fraction(self) -> float:
        return min(1.0, self._position_ / self._total_) if self._total_ else 0.0

    @property
    def remaining(self) -> Union[float, None]:
        if self._pace_ is None or not self._total_: return None
        return max(0.0, self._pace_ * (self._total_ - self._position_))

    def stage(self, label: Union[str, None]) -> None:
        self._label_ = label
        self._render_(force=True)

    def advance(self, step: int = 1) -> None:
        self._position_ += step
        if self._position_ < self._threshold_: return
        self._render_()

    def close(self) -> None:
        if self._closed_: return
        self._closed_ = True
        self._position_ = self._total_ or self._position_
        self._render_(force=True, final=True)
        if self._bar_:
            try: sys.stderr.write("\n"); sys.stderr.flush()
            except Exception: pass

    def _measure_(self, now: float) -> None:
        moved = self._position_ - self._anchor_
        if moved <= 0: return
        sample = (now - self._stamp_) / moved
        self._pace_ = sample if self._pace_ is None else self._pace_ * (1.0 - self._ALPHA_) + sample * self._ALPHA_
        self._anchor_, self._stamp_ = self._position_, now

    def _render_(self, force: bool = False, final: bool = False) -> None:
        try:
            now = time.monotonic()
            if not force and now - self._stamp_ < self._interval_:
                self._threshold_ = self._position_ + self._stride_
                return
            self._measure_(now)
            self._threshold_ = self._position_ + self._stride_
            if self._bar_: self._paint_(now)
            if self._wire_: self._emit_(now, final)
        except Exception:
            self._bar_ = self._wire_ = False

    def _paint_(self, now: float) -> None:
        filled = int(self._WIDTH_ * self.fraction)
        bar = "█" * filled + "·" * (self._WIDTH_ - filled)
        head = f"{self._label_} " if self._label_ else ""
        sys.stderr.write(f"\r{head}[{bar}] {self.fraction * 100.0:5.1f}% · {self._position_:,}/{self._total_:,} {self._unit_}"
                         f" · {seconds_to_clock(now - self._started_)} elapsed · {seconds_to_clock(self.remaining)} left ")
        sys.stderr.flush()

    def _emit_(self, now: float, final: bool) -> None:
        record = {"fraction": round(self.fraction, 4), "position": self._position_, "total": self._total_,
                  "elapsed": round(now - self._started_, 2), "remaining": None if self.remaining is None else round(self.remaining, 2),
                  "stage": self._label_, "unit": self._unit_, "final": final}
        sys.stdout.write(self.SENTINEL + json.dumps(record, separators=(",", ":")) + "\n")
        sys.stdout.flush()