from dash import html
from typing import Any
from dataclasses import dataclass

from Library.App.V2.Component.Component import ButtonAPI, ContainerAPI, IconAPI, TextAPI
from Library.Utility.Typing import MISSING

@dataclass(kw_only=True)
class ChoiceAPI:

    value: str
    label: str
    icon: str = None
    tint: str = None
    tooltip: str = None
    state: Any = MISSING

    def __post_init__(self) -> None:
        if self.state is MISSING: self.state = self.value

class SegmentAPI:

    _CHOICES_: tuple = ()

    def _segment_(self, gate=None) -> ContainerAPI:
        buttons = []
        for choice in self._CHOICES_:
            label = [IconAPI(icon=choice.icon)] if choice.icon else []
            label.append(TextAPI(text=choice.label))
            buttons.append(ButtonAPI(id=getattr(self, self._segment_attribute_(choice)), label=label, background="secondary", classname="app-segment-choice", tooltip=choice.tooltip, disabled=True))
        return ContainerAPI(builder=html.Div, basename="", classname="app-segment", elements=buttons)

    @staticmethod
    def _segment_attribute_(choice: ChoiceAPI) -> str:
        return f"{choice.value.upper()}_SEGMENT"

    def _segment_ids_(self) -> None:
        for choice in self._CHOICES_:
            setattr(self, self._segment_attribute_(choice), self.register(type="segment", name=choice.value.lower()))

    def _segment_choice_(self, trigger) -> str:
        for choice in self._CHOICES_:
            if trigger == getattr(self, self._segment_attribute_(choice)): return choice.value
        return None

    def _segment_state_(self, state, column: str) -> tuple[list, list]:
        rows = list((state or {}).get("rows") or [])
        marked = [row.get(column) for row in rows]
        uniform = marked[0] if marked and all(value == marked[0] for value in marked) else MISSING
        disabled = [not rows for _ in self._CHOICES_]
        active = [uniform is not MISSING and choice.state == uniform for choice in self._CHOICES_]
        return disabled, active