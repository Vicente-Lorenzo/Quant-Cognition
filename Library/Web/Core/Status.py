from datetime import datetime

from dash import html

class StatusAPI:

    _STATUS_COLOR_ = {"Success": "#2f9e44", "Failure": "#ef5350", "Running": "#2962ff", "Waiting": "#868993",
                      "Approving": "#ffb300", "Reviewing": "#ff7043", "Retrying": "#ab47bc"}
    _UNRUN_COLOR_ = "#565a66"
    _NEUTRAL_ = "#868993"
    _LEGEND_ = [("Success", "success"), ("Running", "running"), ("Waiting", "waiting"), ("Approving", "approving"),
                ("Reviewing", "reviewing"), ("Retrying", "retrying"), ("Failure", "failure"), ("No run", "none")]

    @classmethod
    def _legend_(cls) -> html.Div:
        return html.Div([html.Span([html.Span(className=f"led led-{key}"), label]) for label, key in cls._LEGEND_], className="scheduler-legend")

    @classmethod
    def _led_(cls, status) -> str:
        key = status if status in cls._STATUS_COLOR_ else None
        return f'<span class="led-tag"><span class="led led-{key.lower() if key else "none"}"></span>{key or "—"}</span>'

    @classmethod
    def _led_dot_(cls, status):
        key = status if status in cls._STATUS_COLOR_ else None
        return html.Span([html.Span(className=f"led led-{key.lower() if key else 'none'}"), key or "—"], className="led-tag")

    @staticmethod
    def _stamp_(value):
        if isinstance(value, datetime): return value.isoformat(sep=" ", timespec="seconds")
        return value

    @staticmethod
    def _elapsed_(value) -> str:
        if value is None: return ""
        seconds = float(value)
        if seconds < 60: return f"{seconds:.1f}s"
        if seconds < 3600: return f"{seconds // 60:.0f}m {seconds % 60:.0f}s"
        return f"{seconds // 3600:.0f}h {(seconds % 3600) // 60:.0f}m"