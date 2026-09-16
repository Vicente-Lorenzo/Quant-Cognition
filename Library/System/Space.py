from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import dataclass, field
from itertools import product
from typing import Any, Union

from Library.Indicator.Indicator import IndicatorAPI
from Library.Strategy.Range import RangeAPI
from Library.Strategy.Syntax import SyntaxAPI
from Library.Utility.Parameter import Parameter
from Library.Utility.Typing import MISSING

@dataclass(kw_only=True)
class CandidateAPI:

    index: int
    overrides: dict = field(default_factory=dict)

    def label(self) -> str:
        parts = [f"{name}={'/'.join(str(slot) for slot in slots)}"
                 for section in sorted(self.overrides) for name, slots in sorted(self.overrides[section].items())]
        return " · ".join(parts)

    def distance(self, other: CandidateAPI) -> int:
        mine, theirs = self.flatten(), other.flatten()
        return sum(1 for key in set(mine) | set(theirs) if mine.get(key) != theirs.get(key))

    def settings(self) -> dict:
        return {name: "/".join(str(slot) for slot in slots)
                for section in sorted(self.overrides) for name, slots in sorted(self.overrides[section].items())}

    def flatten(self) -> dict:
        return {(section, name, position): slot
                for section, block in self.overrides.items()
                for name, slots in block.items()
                for position, slot in enumerate(slots)}

    def pinned(self) -> dict:
        return {(section, name): list(slots) for section, block in self.overrides.items() for name, slots in block.items()}

class SpaceAPI:

    AUTOMATIC = "Auto"
    SECTIONS = ("MoneyManagement", "RiskManagement", "SignalManagement", "TechnicalManagement", "FundamentalManagement", "SentimentalManagement", "PortfolioManagement")

    _STAGE_ = re.compile(r"^\s*(\d+)\s*(?:-\s*(\d+)\s*)?$")
    _INHERIT_ = re.compile(r"^\s*Result\s*=\s*(\d+)\s*$")

    @staticmethod
    def apply_candidate(base: Parameter, candidate: CandidateAPI) -> Parameter:
        data = deepcopy(base.data)
        for section, block in candidate.overrides.items():
            target = data.get(section)
            if not isinstance(target, dict): continue
            for name, slots in block.items():
                if name in target: target[name] = list(slots)
        return Parameter(data, base.path)

    @classmethod
    def flatten_space(cls, block: Any) -> dict:
        return {section: getattr(getattr(block, section, None), "data", None) for section in cls.SECTIONS}

    @classmethod
    def unpack_plan(cls, block: Any) -> list[dict]:
        flat = cls.flatten_space(block)
        if any(SyntaxAPI.numbered(data) for data in flat.values()): return cls.unpack_stages(block)
        return [flat] if any(isinstance(data, dict) and data for data in flat.values()) else []

    @classmethod
    def staged(cls, block: Any) -> bool:
        return any(SyntaxAPI.numbered(data) for data in cls.flatten_space(block).values())

    @classmethod
    def unpack_stages(cls, block: Any) -> list[dict]:
        stages: dict[int, dict] = {}
        constant: dict = {}
        for section, data in cls.flatten_space(block).items():
            if not isinstance(data, dict) or not data: continue
            if not SyntaxAPI.numbered(data):
                if any(cls._STAGE_.match(str(key)) for key in data):
                    raise ValueError(f"Section {section}: Failed · Mixes stage numbers with parameter names")
                constant[section] = data
                continue
            for key, parameters in data.items():
                match = cls._STAGE_.match(str(key))
                if match is None: raise ValueError(f"Stage key {key!r} in {section}: Failed · Expected a number or a span such as 1-4")
                first = int(match.group(1))
                last = int(match.group(2)) if match.group(2) else first
                if last < first: raise ValueError(f"Stage span {key!r} in {section}: Failed · Ends before it starts")
                for stage in range(first, last + 1):
                    stages.setdefault(stage, {})[section] = parameters
        if not stages: return []
        ordered = sorted(stages)
        if ordered != list(range(1, len(ordered) + 1)):
            raise ValueError(f"Stage numbering {ordered}: Failed · Expected a run starting at 1 with no gaps")
        return [{**constant, **stages[stage]} for stage in ordered]

    @classmethod
    def inherited(cls, value) -> Union[int, None]:
        if not isinstance(value, list) or len(value) != 1 or not isinstance(value[0], str): return None
        match = cls._INHERIT_.match(value[0])
        return int(match.group(1)) if match else None

    @classmethod
    def resolve_inheritance(cls, stage: dict, winners: list, position: int) -> dict:
        resolved = {}
        for section, parameters in (stage or {}).items():
            if not isinstance(parameters, dict):
                resolved[section] = parameters
                continue
            settled = {}
            for name, value in parameters.items():
                reference = cls.inherited(value)
                if reference is None:
                    settled[name] = value
                    continue
                if reference >= position + 1:
                    raise ValueError(f"Result={reference} in {section}.{name}: Failed · Stage {position + 1} cannot inherit from a later stage")
                won = (winners[reference - 1] or {}).get(section, {}).get(name)
                if won is None:
                    raise ValueError(f"Result={reference} in {section}.{name}: Failed · Stage {reference} elected no value for it")
                settled[name] = list(won) if isinstance(won, list) else [won]
            resolved[section] = settled
        return resolved

    @classmethod
    def unpack_section(cls, sections: dict) -> dict:
        space = {}
        for section in cls.SECTIONS:
            data = sections.get(section)
            if not isinstance(data, dict): continue
            for name, slots in data.items():
                if not isinstance(slots, list) or not slots: continue
                options = [slot if isinstance(slot, list) else [slot] for slot in slots]
                if not all(options): continue
                space.setdefault(section, {})[name] = options
        return space

    @classmethod
    def marked(cls, option) -> Union[str, RangeAPI, None]:
        if not isinstance(option, str): return None
        if option.strip().casefold() == cls.AUTOMATIC.casefold(): return cls.AUTOMATIC
        return RangeAPI.parse(option)

    @classmethod
    def declared(cls, head, position: int, options: list) -> tuple:
        if len(options) != 1: return ()
        marker = cls.marked(options[0])
        if marker is None: return ()
        if isinstance(marker, RangeAPI): return marker.ladder()
        if position < 1: return ()
        indicator = IndicatorAPI.resolve_technical(head)
        slots = indicator.Parameters if indicator is not None else ()
        return slots[position - 1].ladder if len(slots) >= position else ()

    @classmethod
    def automatic(cls, options: list) -> bool:
        return len(options) == 1 and cls.marked(options[0]) == cls.AUTOMATIC

    @staticmethod
    def admitted(head, values: list) -> bool:
        indicator = IndicatorAPI.resolve_technical(head)
        if indicator is None: return True
        return indicator.admits({slot.name: values[position] if len(values) > position else slot.default
                                 for position, slot in enumerate(indicator.Parameters, start=1)})

    @classmethod
    def rounds_parameter(cls, options: list) -> int:
        if not options: return 1
        depth = max(1, len(cls.declared(None, 0, options[0])))
        for head in options[0]:
            for position in range(1, len(options)):
                depth = max(depth, len(cls.declared(head, position, options[position])))
        return depth

    @classmethod
    def rounds_space(cls, space: dict) -> int:
        return max((cls.rounds_parameter(options) for section in space for options in space[section].values()), default=1)

    @staticmethod
    def graduate(ladder: tuple, pinned, position: int) -> list:
        if pinned is None: return RangeAPI.sequence(*ladder[0])
        if position >= len(ladder): return [pinned]
        return RangeAPI.window(pinned, *ladder[position], floor=ladder[0][0], ceiling=ladder[0][1]) or [pinned]

    @classmethod
    def expand_parameter(cls, options: list, winner: list = MISSING, position: int = 0, label: str = MISSING) -> list:
        if not options: return []
        where = label or "Parameter"
        pinned = winner if position > 0 and winner else None
        leading = cls.declared(None, 0, options[0])
        if leading: heads = cls.graduate(leading, pinned[0] if pinned else None, position)
        else:
            if cls.automatic(options[0]):
                raise ValueError(f"Optimization Expansion: Failed · {where} leading slot is Auto but Auto only "
                                 f"resolves an indicator's declared ladder · name the indicator or give a list or range")
            heads = [pinned[0]] if pinned else list(options[0])
        values = []
        for head in heads:
            axes = []
            for index in range(1, len(options)):
                ladder = cls.declared(head, index, options[index])
                if not ladder:
                    if cls.automatic(options[index]):
                        raise ValueError(f"Optimization Expansion: Failed · {where} slot {index + 1} is Auto but "
                                         f"{head} declares no ladder for it · give a list or range instead")
                    axes.append([pinned[index]] if pinned else list(options[index]))
                else: axes.append(cls.graduate(ladder, pinned[index] if pinned else None, position))
            for combination in product(*axes):
                candidate = [head, *combination]
                if cls.admitted(head, candidate): values.append(candidate)
        return values

    @classmethod
    def build_grid(cls, space: dict, chosen: dict = MISSING, position: int = 0) -> list[CandidateAPI]:
        axes = [(section, name, cls.expand_parameter(options, (chosen or {}).get((section, name)), position, f"{section}.{name}"))
                for section in sorted(space) for name, options in sorted(space[section].items())]
        if not axes or any(not values for _, _, values in axes): return []
        candidates = []
        for index, combination in enumerate(product(*[values for _, _, values in axes])):
            overrides = {}
            for (section, name, _), slots in zip(axes, combination):
                overrides.setdefault(section, {})[name] = slots
            candidates.append(CandidateAPI(index=index, overrides=overrides))
        return candidates

    @classmethod
    def measure_plan(cls, plan: list) -> int:
        total = 0
        for stage in plan:
            pruned = {section: {name: ([0] if cls.inherited(value) is not None else value) for name, value in parameters.items()}
                      for section, parameters in stage.items() if isinstance(parameters, dict)}
            space = cls.unpack_section(pruned)
            chosen = None
            for position in range(cls.rounds_space(space)):
                grid = cls.build_grid(space, chosen, position)
                if not grid: break
                total += len(grid)
                chosen = grid[len(grid) // 2].pinned()
        return total

    @staticmethod
    def neighborhoods(candidates: list) -> dict:
        buckets, adjacency = {}, {candidate.index: set() for candidate in candidates}
        for candidate in candidates:
            items = tuple(sorted(candidate.flatten().items()))
            for position in range(len(items)):
                wildcard = items[:position] + ((items[position][0], None),) + items[position + 1:]
                buckets.setdefault(wildcard, []).append(candidate.index)
        for members in buckets.values():
            if len(members) < 2: continue
            shared = set(members)
            for index in members: adjacency[index] |= shared
        for index, members in adjacency.items(): members.discard(index)
        return adjacency

__all__ = ["CandidateAPI", "SpaceAPI"]