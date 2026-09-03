from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Union

@dataclass(frozen=True)
class RangeAPI:

    _PATTERN_ = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*(?:\.\.|-)\s*(-?\d+(?:\.\d+)?)\s*(?::\s*(\d+(?:\.\d+)?)\s*)?$")
    _DEPTH_ = 3

    Low: Union[int, float]
    High: Union[int, float]
    Step: Union[int, float] = 1

    @staticmethod
    def _number_(value: Decimal) -> Union[int, float]:
        return int(value) if value == value.to_integral_value() else float(value)

    @classmethod
    def sequence(cls, low, high, step) -> list:
        first, last = Decimal(str(low)), Decimal(str(high))
        stride = abs(Decimal(str(step or 1)))
        whole = all(part == part.to_integral_value() for part in (first, last, stride))
        values, cursor = [], first
        while cursor <= last:
            values.append(cls._number_(cursor) if whole else float(cursor))
            cursor += stride
        return values or [cls._number_(first) if whole else float(first)]

    @classmethod
    def window(cls, center, low, high, step, floor=None, ceiling=None) -> list:
        anchor = Decimal(str(center))
        values = cls.sequence(anchor + Decimal(str(low)), anchor + Decimal(str(high)), step)
        if floor is not None: values = [value for value in values if value >= floor]
        if ceiling is not None: values = [value for value in values if value <= ceiling]
        return values

    @classmethod
    def parse(cls, value) -> Union[RangeAPI, None]:
        if isinstance(value, RangeAPI): return value
        if not isinstance(value, str): return None
        found = cls._PATTERN_.match(value)
        if found is None: return None
        low, high, step = (Decimal(part) if part is not None else None for part in found.groups())
        if high < low: return None
        return cls(Low=cls._number_(low), High=cls._number_(high), Step=cls._number_(step) if step else 1)

    def ladder(self) -> tuple:
        stride = Decimal(str(self.Step))
        whole = stride == stride.to_integral_value()
        rounds = [(self.Low, self.High, self.Step)]
        while len(rounds) < self._DEPTH_:
            if whole and stride <= 1: break
            stride = max(Decimal(1), stride // 2) if whole else stride / 2
            rounds.append((self._number_(-2 * stride), self._number_(2 * stride), self._number_(stride)))
        return tuple(rounds)