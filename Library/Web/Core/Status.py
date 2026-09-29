from datetime import datetime

from dash import html

from Library.Scheduler import RunStatus

class StatusAPI:

    _STATUS_COLOR_ = {RunStatus.Waiting.name: "#868993", RunStatus.Initializing.name: "#4fc3f7", RunStatus.Running.name: "#2962ff", RunStatus.Terminating.name: "#78909c",
                      RunStatus.Approving.name: "#ffb300", RunStatus.Reviewing.name: "#ff7043", RunStatus.Retrying.name: "#ab47bc", RunStatus.Success.name: "#2f9e44",
                      RunStatus.Failure.name: "#ef5350"}
    _LEGEND_ = [(RunStatus.Waiting.name, "waiting"), (RunStatus.Initializing.name, "initializing"), (RunStatus.Running.name, "running"), (RunStatus.Terminating.name, "terminating"),
                (RunStatus.Approving.name, "approving"), (RunStatus.Reviewing.name, "reviewing"), (RunStatus.Retrying.name, "retrying"), (RunStatus.Success.name, "success"),
                (RunStatus.Failure.name, "failure"), ("No run", "none")]

    @classmethod
    def _key_(cls, status) -> str | None:
        return status if status in cls._STATUS_COLOR_ else None

    @classmethod
    def _legend_(cls) -> html.Div:
        return html.Div([html.Span([html.Span(className=f"led led-{key}"), label]) for label, key in cls._LEGEND_], className="scheduler-legend")

    @classmethod
    def _led_(cls, status) -> str:
        key = cls._key_(status)
        return f'<span class="led-tag"><span class="led led-{key.lower() if key else "none"}"></span>{key or "—"}</span>'

    @classmethod
    def _led_dot_(cls, status):
        key = cls._key_(status)
        return html.Span([html.Span(className=f"led led-{key.lower() if key else 'none'}"), key or "—"], className="led-tag")

    @staticmethod
    def _stamp_(value):
        if not isinstance(value, datetime): return value
        text = value.isoformat(sep=" ", timespec="seconds")
        return html.Span(text, **{"data-utc": text})

    @staticmethod
    def _elapsed_(value) -> str:
        if value is None: return ""
        seconds = float(value)
        if seconds < 60: return f"{seconds:.1f}s"
        if seconds < 3600: return f"{seconds // 60:.0f}m {seconds % 60:.0f}s"
        return f"{seconds // 3600:.0f}h {(seconds % 3600) // 60:.0f}m"