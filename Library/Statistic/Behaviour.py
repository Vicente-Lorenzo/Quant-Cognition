from typing import Union

from Library.Database.Dataframe import np

def sidedness(exposure: np.ndarray) -> tuple[float, float, float]:
    active = int(np.count_nonzero(exposure))
    if not active: return 0.0, 0.0, 0.0
    longs = float(np.count_nonzero(exposure > 0.0)) / active
    return active / exposure.size, longs, min(longs, 1.0 - longs)

def runs(exposure: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    signs = np.sign(exposure).astype(np.int8)
    if not signs.size: return np.empty(0, dtype=np.int64), np.empty(0, dtype=np.int8)
    edges = np.flatnonzero(np.diff(signs)) + 1
    starts, stops = np.concatenate(([0], edges)), np.concatenate((edges, [signs.size]))
    directional = signs[starts] != 0
    return (stops - starts)[directional], signs[starts][directional]

def persistence(exposure: np.ndarray, bars_per_day: float = 24.0) -> dict:
    lengths, directions = runs(exposure)
    if not lengths.size: return {"Runs": 0, "MeanHoldDays": 0.0, "MedianHoldDays": 0.0, "LongestDays": 0.0, "Flips": 0}
    days = lengths / bars_per_day
    held = {f"HeldBeyond{threshold}Days": float(lengths[days >= threshold].sum() / lengths.sum()) for threshold in (1, 7, 30, 90)}
    return {"Runs": int(lengths.size), "MeanHoldDays": float(days.mean()), "MedianHoldDays": float(np.median(days)), "LongestDays": float(days.max()), "Flips": int(np.count_nonzero(np.diff(directions))), **held}

def regime(exposure: np.ndarray, closes: np.ndarray, years: np.ndarray, minimum: int = 100) -> Union[float, None]:
    numerator = denominator = 0.0
    for year in np.unique(years):
        mask = years == year
        held = exposure[mask]
        active = np.count_nonzero(held)
        if mask.sum() < minimum or active < minimum: continue
        prices = closes[mask]
        move = prices[-1] / prices[0] - 1.0
        longs = np.count_nonzero(held > 0.0) / active
        numerator += (longs if move > 0.0 else 1.0 - longs) * abs(move)
        denominator += abs(move)
    return 100.0 * numerator / denominator if denominator else None

def null(exposure: np.ndarray, closes: np.ndarray, years: np.ndarray, draws: int = 2000, seed: int = 0) -> dict:
    observed = regime(exposure, closes, years)
    if observed is None or exposure.size < 2: return {"Regime": observed, "NullMedian": None, "P": None, "Z": None}
    shifts = np.random.default_rng(seed).integers(1, exposure.size, size=draws)
    scores = np.array([score for score in (regime(np.roll(exposure, int(shift)), closes, years) for shift in shifts) if score is not None])
    if not scores.size: return {"Regime": observed, "NullMedian": None, "P": None, "Z": None}
    deviation = scores.std()
    return {"Regime": observed, "NullMedian": float(np.median(scores)), "Null5": float(np.percentile(scores, 5)), "Null95": float(np.percentile(scores, 95)),
            "P": max(0.0005, float((np.count_nonzero(scores >= observed) + 1) / (scores.size + 1))), "Z": float((observed - scores.mean()) / deviation) if deviation else None}

def exposure_beta(model: np.ndarray, market: np.ndarray) -> tuple[Union[float, None], Union[float, None]]:
    if model.size < 2 or market.size != model.size: return None, None
    variance = float(np.var(market, ddof=1))
    if not variance: return None, None
    beta = float(np.cov(model, market, ddof=1)[0, 1]) / variance
    return beta, float(model.mean() - beta * market.mean())