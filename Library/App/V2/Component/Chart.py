import io
import base64
from typing import Any
from dash import dcc, html
from dataclasses import dataclass

from Library.App.V2.Component.Component import ComponentAPI, Component, ImageAPI, IframeAPI, prop
from Library.Utility.Typing import MISSING

@dataclass(kw_only=True)
class PlotlyAPI(ComponentAPI):

    classname: str = "plotly"
    builder: type[Component] = dcc.Graph

    figure: Any = prop()
    config: dict = prop()
    responsive: bool | str = prop(default=True)

@dataclass(kw_only=True)
class NetworkAPI(PlotlyAPI):

    classname: str = "network"

    nodes: list = MISSING
    edges: list = MISSING
    tint: str = "#868993"
    fallback: str = "#565a66"
    placeholder: str = "No nodes"
    anchor: str = MISSING

    _CONFIG_ = {"displayModeBar": False, "displaylogo": False, "scrollZoom": False, "doubleClick": False}
    _AXIS_ = {"visible": False, "fixedrange": True}
    _ARROW_ = 0.42
    _HEAD_ = 0.60

    @classmethod
    def layout(cls, figure, tint: str, reversed: bool = False):
        vertical = {**cls._AXIS_, "autorange": "reversed"} if reversed else cls._AXIS_
        figure.update_layout(
            showlegend=False,
            margin={"l": 8, "r": 8, "t": 8, "b": 8},
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            dragmode=False,
            xaxis=cls._AXIS_,
            yaxis=vertical,
            font={"color": tint}
        )
        return figure

    @classmethod
    def blank(cls, text: str, tint: str = "#868993"):
        import plotly.graph_objects as go
        figure = go.Figure()
        figure.update_layout(annotations=[{"text": text, "showarrow": False, "xref": "paper", "yref": "paper", "x": 0.5, "y": 0.5, "font": {"color": tint, "size": 13}}])
        return cls.layout(figure, tint)

    @staticmethod
    def graph(nodes: list, edges: list):
        import networkx as nx
        keys = [node["uid"] for node in nodes]
        graph = nx.DiGraph()
        graph.add_nodes_from(keys)
        graph.add_edges_from([(predecessor, successor) for predecessor, successor in edges if predecessor in keys and successor in keys])
        if not nx.is_directed_acyclic_graph(graph): return None
        for layer, members in enumerate(nx.topological_generations(graph)):
            for node in members: graph.nodes[node]["layer"] = layer
        return graph

    @classmethod
    def span(cls, nodes: list, edges: list) -> int:
        graph = cls.graph(nodes, edges) if nodes else None
        if graph is None: return len(nodes)
        layers = {}
        for node in graph.nodes(): layers.setdefault(graph.nodes[node]["layer"], 0)
        for node in graph.nodes(): layers[graph.nodes[node]["layer"]] += 1
        return max(layers.values(), default=0)

    @classmethod
    def order(cls, nodes: list, edges: list) -> list:
        graph = cls.graph(nodes, edges) if nodes else None
        if graph is None: return [node["uid"] for node in nodes]
        return sorted(graph.nodes(), key=lambda node: (graph.nodes[node]["layer"], node))

    @classmethod
    def render(cls, nodes: list, edges: list, tint: str = "#868993", fallback: str = "#565a66", placeholder: str = "No nodes"):
        import networkx as nx
        import plotly.graph_objects as go
        if not nodes: return cls.blank(placeholder, tint)
        graph = cls.graph(nodes, edges)
        if graph is None: return cls.blank("Dependency cycle detected", tint)
        position = nx.multipartite_layout(graph, subset_key="layer")
        ordered = list(graph.nodes())
        catalog = {node["uid"]: node for node in nodes}
        horizontal, vertical, arrows = [], [], []
        for predecessor, successor in graph.edges():
            ax, ay = position[predecessor]
            bx, by = position[successor]
            horizontal += [ax, bx, None]
            vertical += [ay, by, None]
            arrows.append({"ax": ax + (bx - ax) * cls._ARROW_, "ay": ay + (by - ay) * cls._ARROW_,
                           "x": ax + (bx - ax) * cls._HEAD_, "y": ay + (by - ay) * cls._HEAD_,
                           "xref": "x", "yref": "y", "axref": "x", "ayref": "y", "showarrow": True,
                           "arrowhead": 2, "arrowsize": 1.2, "arrowwidth": 2.4, "arrowcolor": tint})
        figure = go.Figure()
        figure.add_trace(go.Scatter(x=horizontal, y=vertical, mode="lines", hoverinfo="skip", line={"color": tint, "width": 2.4, "shape": "spline"}))
        figure.add_trace(go.Scatter(x=[position[node][0] for node in ordered], y=[position[node][1] for node in ordered],
                                    mode="markers+text", customdata=ordered, hoverinfo="none",
                                    marker={"size": 26, "color": [catalog[node].get("color") or fallback for node in ordered],
                                            "line": {"width": 0}, "symbol": "circle", "opacity": 1},
                                    text=ordered, textposition="bottom center",
                                    textfont={"color": tint, "size": 11.5, "family": "inherit"}))
        figure.update_layout(annotations=arrows)
        return cls.layout(figure, tint, reversed=True)

    def __post_init__(self):
        super().__post_init__()
        if self.config is MISSING: self.config = self._CONFIG_
        if self.figure is MISSING:
            self.figure = self.render(self.nodes or [], self.edges or [], self.tint, self.fallback, self.placeholder) if self.nodes is not MISSING else self.blank(self.placeholder, self.tint)

    def build(self) -> list[Component]:
        graph = super().build()
        if self.anchor is MISSING: return graph
        return [html.Div(graph, className="network-host", **{"data-open": self.anchor})]

@dataclass(kw_only=True)
class MatplotlibAPI(ImageAPI):

    classname: str = "matplotlib"

    figure: Any = MISSING

    def generate(self) -> str:
        if self.figure is MISSING: return ""
        fig = self.figure
        if hasattr(fig, "flat"): fig = fig.flat[0]
        if hasattr(fig, "figure"): fig = fig.figure
        if hasattr(fig, "savefig"):
            buf = io.BytesIO()
            fig.savefig(buf, format="png", bbox_inches="tight", transparent=True)
            buf.seek(0)
            encoded = base64.b64encode(buf.read()).decode("utf-8")
            return f"data:image/png;base64,{encoded}"
        return ""

    def arguments(self) -> dict:
        if self.src is MISSING: self.src = self.generate()
        return super().arguments()

@dataclass(kw_only=True)
class BokehAPI(IframeAPI):

    classname: str = "bokeh"

    figure: Any = MISSING

    def generate(self) -> str:
        if self.figure is MISSING: return ""
        from bokeh.embed import file_html
        from bokeh.resources import CDN
        return file_html(self.figure, CDN, "Bokeh Plot")

    def arguments(self) -> dict:
        if self.srcdoc is MISSING: self.srcdoc = self.generate()
        return super().arguments()

@dataclass(kw_only=True)
class AltairAPI(IframeAPI):

    classname: str = "altair"

    figure: Any = MISSING

    def generate(self) -> str:
        if self.figure is MISSING: return ""
        html = self.figure.to_html()
        style = "<style>html, body, #vis { width: 100%; height: 100%; margin: 0; padding: 0; overflow: hidden; }</style>"
        return html.replace("<head>", f"<head>\n{style}") if "<head>" in html else f"{style}\n{html}"

    def arguments(self) -> dict:
        if self.srcdoc is MISSING: self.srcdoc = self.generate()
        return super().arguments()

@dataclass(kw_only=True)
class PanelAPI(IframeAPI):

    classname: str = "panel"

    figure: Any = MISSING

    def generate(self) -> str:
        if self.figure is MISSING: return ""
        buf = io.StringIO()
        self.figure.save(buf)
        return buf.getvalue()

    def arguments(self) -> dict:
        if self.srcdoc is MISSING: self.srcdoc = self.generate()
        return super().arguments()

@dataclass(kw_only=True)
class HoloviewsAPI(ComponentAPI):

    classname: str = "holoviews"

    figure: Any = MISSING
    config: dict = MISSING

    def build(self) -> list[Component]:
        if self.figure is MISSING: return super().build()
        import holoviews as hv
        rendered = hv.render(self.figure)
        kwargs = {k: v for k, v in self.__dict__.items() if k not in ["element", "builder", "classname", "figure", "config"]}
        return ChartAPI(figure=rendered, config=self.config, **kwargs).build()

@dataclass(kw_only=True)
class ChartAPI(ComponentAPI):

    classname: str = "chart"

    figure: Any = MISSING
    config: dict = MISSING

    def build(self) -> list[Component]:
        fig = self.figure
        fig_module = type(fig).__module__ if fig is not MISSING else ""
        kwargs = {k: v for k, v in self.__dict__.items() if k not in ["element", "builder", "classname", "config"]}
        if fig is MISSING or "plotly" in fig_module or isinstance(fig, dict):
            return PlotlyAPI(config=self.config, **kwargs).build()
        elif "matplotlib" in fig_module or "seaborn" in fig_module:
            return MatplotlibAPI(**kwargs).build()
        elif "bokeh" in fig_module:
            return BokehAPI(**kwargs).build()
        elif "altair" in fig_module:
            return AltairAPI(**kwargs).build()
        elif "panel" in fig_module:
            return PanelAPI(**kwargs).build()
        elif "holoviews" in fig_module:
            return HoloviewsAPI(config=self.config, **kwargs).build()
        else:
            if hasattr(fig, "figure"):
                return MatplotlibAPI(**kwargs).build()
            return PlotlyAPI(config=self.config, **kwargs).build()