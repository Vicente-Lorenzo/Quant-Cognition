import io
import base64
from dash import dcc
from typing import Union, Any
from dataclasses import dataclass, field

from Library.App.V1.Component import ComponentAPI, Component, ImageAPI, IframeAPI

@dataclass(kw_only=True)
class PlotlyAPI(ComponentAPI):

    classname: Union[str, None] = field(default="plotly")
    builder: type[Component] = field(default=dcc.Graph)

    figure: Any = field(default=None)
    config: dict = field(default=None)
    responsive: Union[bool, str] = field(default=True)

    def arguments(self) -> dict:
        kwargs = super().arguments()
        if self.figure is not None: kwargs.update(figure=self.figure)
        if self.config is not None: kwargs.update(config=self.config)
        if self.responsive is not None: kwargs.update(responsive=self.responsive)
        return kwargs

@dataclass(kw_only=True)
class MatplotlibAPI(ImageAPI):

    classname: Union[str, None] = field(default="matplotlib")

    figure: Any = field(default=None)

    def generate(self) -> str:
        if self.figure is None: return ""
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
        if self.src is None:
            self.src = self.generate()
        return super().arguments()

@dataclass(kw_only=True)
class BokehAPI(IframeAPI):

    classname: Union[str, None] = field(default="bokeh")

    figure: Any = field(default=None)

    def generate(self) -> str:
        if self.figure is None: return ""
        from bokeh.embed import file_html
        from bokeh.resources import CDN
        return file_html(self.figure, CDN, "Bokeh Plot")

    def arguments(self) -> dict:
        if self.srcdoc is None:
            self.srcdoc = self.generate()
        return super().arguments()

@dataclass(kw_only=True)
class AltairAPI(IframeAPI):

    classname: Union[str, None] = field(default="altair")

    figure: Any = field(default=None)

    def generate(self) -> str:
        if self.figure is None: return ""
        html = self.figure.to_html()
        style = "<style>html, body, #vis { width: 100%; height: 100%; margin: 0; padding: 0; overflow: hidden; }</style>"
        return html.replace("<head>", f"<head>\n{style}") if "<head>" in html else f"{style}\n{html}"

    def arguments(self) -> dict:
        if self.srcdoc is None:
            self.srcdoc = self.generate()
        return super().arguments()

@dataclass(kw_only=True)
class PanelAPI(IframeAPI):

    classname: Union[str, None] = field(default="panel")

    figure: Any = field(default=None)

    def generate(self) -> str:
        if self.figure is None: return ""
        buf = io.StringIO()
        self.figure.save(buf)
        return buf.getvalue()

    def arguments(self) -> dict:
        if self.srcdoc is None:
            self.srcdoc = self.generate()
        return super().arguments()

@dataclass(kw_only=True)
class HoloviewsAPI(ComponentAPI):

    classname: Union[str, None] = field(default="holoviews")

    figure: Any = field(default=None)
    config: dict = field(default=None)

    def build(self) -> list[Component]:
        if self.figure is None: return super().build()
        import holoviews as hv
        rendered = hv.render(self.figure)
        kwargs = {k: v for k, v in self.__dict__.items() if k not in ["element", "builder", "figure"]}
        return ChartAPI(figure=rendered, config=self.config, **kwargs).build()

@dataclass(kw_only=True)
class ChartAPI(ComponentAPI):

    classname: Union[str, None] = field(default="chart")

    figure: Any = field(default=None)
    config: dict = field(default=None)

    def build(self) -> list[Component]:
        fig = self.figure
        fig_module = type(fig).__module__ if fig is not None else ""
        kwargs = {k: v for k, v in self.__dict__.items() if k not in ["element", "builder", "classname", "config"]}
        if fig is None or "plotly" in fig_module or isinstance(fig, dict):
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