from __future__ import annotations

from statistics import fmean, median
from typing import Any, Callable, Union

from Library.Utility.Enumeration import EnumerationAPI

class SelectionMode(EnumerationAPI):
    Worst = 1
    Plateau = 2
    Mean = 3
    Median = 4
    Best = 5

class ElectionMode(EnumerationAPI):
    First = 1
    Worst = 2
    Frequency = 3
    Mean = 4
    Median = 5
    Best = 6
    Last = 7

def _ranked_(scored: list) -> list:
    return [(item, score) for item, score in scored if score is not None]

def _nearest_(ranked: list, target: float) -> tuple:
    return min(ranked, key=lambda entry: abs(entry[1] - target))

def select(scored: list, mode: Union[str, SelectionMode] = SelectionMode.Best,
           adjacency: Union[Callable, None] = None) -> Union[tuple, None]:
    ranked = _ranked_(scored)
    if not ranked: return None
    resolved = mode if isinstance(mode, SelectionMode) else SelectionMode.parse(mode)
    if resolved is SelectionMode.Best: return max(ranked, key=lambda entry: entry[1])
    if resolved is SelectionMode.Worst: return min(ranked, key=lambda entry: entry[1])
    if resolved is SelectionMode.Mean: return _nearest_(ranked, fmean(score for _, score in ranked))
    if resolved is SelectionMode.Median: return _nearest_(ranked, median(score for _, score in ranked))
    if adjacency is None: return max(ranked, key=lambda entry: entry[1])
    company = adjacency([item for item, _ in ranked])
    lookup = {getattr(item, "index", index): score for index, (item, score) in enumerate(ranked)}
    best, summit = None, None
    for item, score in ranked:
        neighbours = [lookup[key] for key in company.get(getattr(item, "index", None), ()) if key in lookup]
        plateau = (score + sum(neighbours)) / (1 + len(neighbours))
        if summit is None or plateau > summit: best, summit = (item, score), plateau
    return best

def elect(records: list, mode: Union[str, ElectionMode] = ElectionMode.Frequency) -> Union[tuple, None]:
    entries = [record for record in records if record.get("Key") is not None]
    if not entries: return None
    resolved = mode if isinstance(mode, ElectionMode) else ElectionMode.parse(mode)
    if resolved is ElectionMode.First: return entries[0]["Key"], {"Reason": "First fold"}
    if resolved is ElectionMode.Last: return entries[-1]["Key"], {"Reason": "Last fold"}
    tally: dict[Any, list] = {}
    order: dict[Any, int] = {}
    for position, record in enumerate(entries):
        tally.setdefault(record["Key"], []).append(record.get("Score"))
        order.setdefault(record["Key"], position)
    scored = {key: [score for score in values if score is not None] for key, values in tally.items()}
    if resolved is ElectionMode.Frequency:
        winner = max(tally, key=lambda key: (len(tally[key]), sum(scored[key]), -order[key]))
        return winner, {"Reason": "Most selected", "Votes": len(tally[winner]), "Folds": len(entries)}
    ranked = {key: values for key, values in scored.items() if values}
    if not ranked: return entries[-1]["Key"], {"Reason": "No fold produced a score"}
    if resolved is ElectionMode.Mean: statistic = {key: fmean(values) for key, values in ranked.items()}
    elif resolved is ElectionMode.Median: statistic = {key: median(values) for key, values in ranked.items()}
    elif resolved is ElectionMode.Worst: statistic = {key: min(values) for key, values in ranked.items()}
    else: statistic = {key: max(values) for key, values in ranked.items()}
    chooser = min if resolved is ElectionMode.Worst else max
    winner = chooser(statistic, key=lambda key: (statistic[key], -order[key]))
    return winner, {"Reason": resolved.name, "Statistic": statistic[winner], "Folds": len(entries)}

__all__ = ["ElectionMode", "SelectionMode", "elect", "select"]