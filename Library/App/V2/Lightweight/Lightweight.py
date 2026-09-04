import json
from dash import html
from typing import Any
from dataclasses import dataclass

from Library.App.V2.Component.Component import Component, ComponentAPI, StorageAPI
from Library.Statistic.Workspace import PointAPI, WorkspaceAPI
from Library.Utility.Typing import MISSING

@dataclass(kw_only=True)
class LightweightAPI(ComponentAPI):

    classname: str = "lightweight"
    builder: type[Component] = html.Div
    role: str = "chart"

    workspace: str = "default"
    payload: Any = MISSING
    carrier: dict = MISSING
    selection: dict = MISSING
    edition: dict = MISSING
    height: str = MISSING

    _FILL_ = "fill"

    def __post_init__(self):
        super().__post_init__()
        if self.height is not MISSING and self.height != self._FILL_: self.style = {**self.style, "maxHeight": self.height}

    def arguments(self) -> dict:
        arguments = {**super().arguments(), "data-workspace": self.workspace, "data-role": self.role}
        if self.height == self._FILL_: arguments["data-fill"] = "1"
        return arguments

    def encode(self) -> str:
        payload = self.payload
        if payload is MISSING or payload is None: return "{}"
        if isinstance(payload, WorkspaceAPI):
            if self.selection is not MISSING and payload.outbound is None: payload.outbound = self.selection
            if self.edition is not MISSING and payload.edition is None: payload.edition = self.edition
            return payload.encode()
        if isinstance(payload, str): return payload
        data = dict(payload)
        if self.selection is not MISSING: data.setdefault("outbound", self.selection)
        if self.edition is not MISSING: data.setdefault("edition", self.edition)
        return json.dumps(PointAPI.compact(data), default=str, separators=(",", ":"))

    def build(self) -> list[Component]:
        carrier = {"id": self.carrier} if self.carrier is not MISSING else {}
        elements = [html.Script(self.encode(), type="application/json", className="lightweight-payload", **carrier),
                    html.Div(className="lightweight-body")]
        hidden = [StorageAPI(id=self.selection, data=None)] if self.selection is not MISSING else []
        if self.edition is not MISSING: hidden.append(StorageAPI(id=self.edition, data=None))
        host = self.builder(elements, **self.arguments())
        return self.serialize([host], self.flatten(hidden))

@dataclass(kw_only=True)
class LightweightChartAPI(LightweightAPI):

    typename: str = "lightweight-chart"
    role: str = "chart"

@dataclass(kw_only=True)
class LightweightTableAPI(LightweightAPI):

    typename: str = "lightweight-table"
    role: str = "table"