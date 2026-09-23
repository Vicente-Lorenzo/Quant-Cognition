from Library.Database.Dataframe import np
from Library.Statistic.Metric import series_returns
from Library.Utility.Math import EPSILON

def underwater(equity: list) -> list:
    peak, series = None, []
    for stamp, value in equity:
        if value is None: continue
        peak = value if peak is None or value > peak else peak
        series.append((stamp, ((value / peak) - 1.0) * 100.0 if peak else 0.0))
    return series

def overwater(equity: list) -> list:
    peak, trough, series = None, None, []
    for stamp, value in equity:
        if value is None: continue
        if peak is None or value > peak: peak, trough = value, value
        elif trough is None or value < trough: trough = value
        series.append((stamp, ((value / trough) - 1.0) * 100.0 if trough else 0.0))
    return series

def periodic(equity: list) -> list:
    closes, order = {}, []
    for stamp, value in equity:
        if value is None: continue
        moment = stamp if hasattr(stamp, "year") else None
        if moment is None: continue
        key = (moment.year, moment.month)
        if key not in closes: order.append(key)
        closes[key] = value
    if not order: return []
    opening = next((value for _, value in equity if value is not None), None)
    rows, previous, years = [], opening, {}
    for key in order:
        year, month = key
        current = closes[key]
        if previous: years.setdefault(year, {})[month] = ((current / previous) - 1.0) * 100.0
        previous = current
    months = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
    for year in sorted(years):
        row = {"Year": str(year)}
        compounded = 1.0
        for index, name in enumerate(months, start=1):
            value = years[year].get(index)
            row[name] = None if value is None else round(value, 2)
            if value is not None: compounded *= 1.0 + value / 100.0
        row["Year Total"] = round((compounded - 1.0) * 100.0, 2)
        rows.append(row)
    return rows

def _windows_(values: list, window: int, chunk: int = 16384):
    array = np.asarray(values, dtype=np.float64)
    for offset in range(0, array.size - window + 1, chunk):
        yield offset, np.lib.stride_tricks.sliding_window_view(array[offset:offset + chunk + window - 1], window)

def rolling(equity: list, window: int = 63, periods: float = 252.0) -> tuple:
    values = [(stamp, value) for stamp, value in equity if value is not None]
    if len(values) <= window: return [], []
    returns = [(values[index][0], values[index][1] / values[index - 1][1] - 1.0)
               for index in range(1, len(values)) if values[index - 1][1]]
    scale = periods ** 0.5
    sharpes, volatilities = [], []
    for offset, block in _windows_([value for _, value in returns], window):
        for index, (mean, deviation) in enumerate(zip(block.mean(axis=1).tolist(), block.std(axis=1, ddof=1).tolist()), start=offset + window - 1):
            volatilities.append((returns[index][0], deviation * scale * 100.0))
            sharpes.append((returns[index][0], (mean / deviation) * scale if deviation > EPSILON else 0.0))
    return sharpes, volatilities

def covariant(equity: list, benchmark: list, window: int = 63) -> list:
    if not equity or not benchmark: return []
    reference = dict(benchmark)
    paired = [(stamp, value, reference[stamp]) for stamp, value in equity if value is not None and reference.get(stamp) is not None]
    if len(paired) <= window: return []
    returns = []
    for index in range(1, len(paired)):
        previous, current = paired[index - 1], paired[index]
        if not previous[1] or not previous[2]: continue
        returns.append((current[0], current[1] / previous[1] - 1.0, current[2] / previous[2] - 1.0))
    betas = []
    for (offset, mine), (_, theirs) in zip(_windows_([first for _, first, _ in returns], window), _windows_([second for _, _, second in returns], window)):
        mine = mine - mine.mean(axis=1, keepdims=True)
        theirs = theirs - theirs.mean(axis=1, keepdims=True)
        covariances, variances = (mine * theirs).sum(axis=1).tolist(), (theirs * theirs).sum(axis=1).tolist()
        for index, (covariance, variance) in enumerate(zip(covariances, variances), start=offset + window - 1):
            betas.append((returns[index][0], covariance / variance if variance > EPSILON * EPSILON else 0.0))
    return betas

def distribution(equity: list, buckets: int = 41) -> list:
    values = [value for _, value in equity if value is not None]
    returns = [value for value in series_returns(values) if value is not None]
    if len(returns) < buckets: return []
    lowest, highest = min(returns), max(returns)
    if highest <= lowest: return []
    width = (highest - lowest) / buckets
    counts = [0] * buckets
    for value in returns:
        index = min(int((value - lowest) / width), buckets - 1)
        counts[index] += 1
    return [((lowest + (index + 0.5) * width) * 100.0, count) for index, count in enumerate(counts)]

__all__ = ["underwater", "overwater", "periodic", "rolling", "covariant", "distribution"]