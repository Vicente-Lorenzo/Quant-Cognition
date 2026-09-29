import math

EPSILON: float = 1e-8

def equals(a: float, b: float, tolerance: float = EPSILON) -> bool:
    return abs(a - b) <= tolerance * max(1.0, abs(a), abs(b))

def truncate(value: float, digits: int = 2, tolerance: float = EPSILON) -> float:
    scale = 10.0 ** digits
    scaled = value * scale
    scaled = math.floor(scaled + tolerance) if value >= 0.0 else math.ceil(scaled - tolerance)
    return scaled / scale

def quantize(value: float, digits: int = 2, tolerance: float = EPSILON) -> float:
    scale = 10.0 ** digits
    scaled = math.floor(abs(value) * scale + 0.5 + tolerance)
    if not scaled: return 0.0
    return scaled / scale if value >= 0.0 else -scaled / scale