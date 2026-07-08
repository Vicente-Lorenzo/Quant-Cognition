import io
import base64
from dash import dcc
from typing import Any
from dataclasses import dataclass

from Library.App.V2.Component import ComponentAPI, Component, ImageAPI, IframeAPI, prop
from Library.Utility.Typing import MISSING

@dataclass(kw_only=True)
class PlotlyAPI(ComponentAPI):

    classname: str = "plotly"
    builder: type[Component] = dcc.Graph

    figure: Any = prop()
    config: dict = prop()
    responsive: bool | str = prop(default=True)

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
        kwargs = {k: v for k, v in self.__dict__.items() if k not in ["element", "builder", "figure", "config"]}
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