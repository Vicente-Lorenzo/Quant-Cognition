import math

def equals(a: float, b: float, rel: float = 1e-12, abs_: float = 1e-12) -> bool:
    return abs(a - b) <= max(rel * max(1.0, abs(a), abs(b)), abs_)

def truncate(value: float, digits: int = 2) -> float:
    scale = 10.0 ** digits
    scaled = value * scale
    scaled = math.floor(scaled + 1e-6) if value >= 0.0 else math.ceil(scaled - 1e-6)
    return scaled / scale