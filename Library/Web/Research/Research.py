from dash import html

from Library.App.V2 import SectionPageAPI
from Library.Web.Research.Launch import LaunchAPI, LaunchFieldsAPI
from Library.Web.Research.Result import ResultPageAPI, ResultsPageAPI, LaunchedResultsPageAPI

class ResearchBaseAPI:

    RESEARCH = ("Research.Backtesting", "Research.Optimization", "Research.Learning")

    _ANCHOR_ = "/research"

    @staticmethod
    def _research_(run: dict) -> str:
        return str(run.get("TID") or "").split(".")[-1]

class ResearchPageAPI(ResearchBaseAPI, SectionPageAPI):

    _FAMILY_ = "Research"

    def __init__(self, *, app) -> None:
        super().__init__(app=app, path="/research", button="Research", icon="bi bi-clipboard-data", description="Backtest, optimize and train — every run in one place")

class ResearchRunPageAPI(ResearchBaseAPI, LaunchedResultsPageAPI):

    _FAMILY_ = "Research"
    _TASK_ = ResearchBaseAPI.RESEARCH
    _TASKS_ = LaunchFieldsAPI.TASKS
    _SYSTEMS_ = LaunchFieldsAPI.SYSTEMS
    _LAUNCH_ = LaunchFieldsAPI.EVERY
    _COLUMNS_ = ["Status", "UID", "Research", "Retention", "StartedAt", "StoppedAt", "Duration", "Progress", "Artifacts"]

    def __init__(self, *, app) -> None:
        super().__init__(app=app, path="/research/all", button="Journal", icon="bi bi-journal-text", description="Every backtest, optimization and learning run together")

    def _launch_button_(self):
        button = super()._launch_button_()
        button.label = self._icon_("bi bi-play-fill", "Run Research", tint="success")
        button.tooltip = "Configure and dispatch a backtest, optimization or learning run"
        return button

    def _row_(self, run: dict, produced: list, fields: dict) -> dict | None:
        return {**super()._row_(run, produced, fields), "Research": self._research_(run), "Progress": self._percentage_(run)}

    @staticmethod
    def _percentage_(run: dict) -> str:
        fraction = run.get("Progress")
        if fraction is None: return ""
        return f"{float(fraction) * 100.0:.0f}%"

    _open_launch_, _close_launch_, _submit_launch_ = LaunchAPI.launch_callbacks(_LAUNCH_)

class ResearchResultPageAPI(ResearchBaseAPI, ResultPageAPI):

    _FAMILY_ = "Result"
    _LAUNCH_ = LaunchFieldsAPI.EVERY

    def __init__(self, *, app) -> None:
        super().__init__(app=app, path="/research/:uid", button="Result", icon="bi bi-clipboard-data", parametric=True)

class ResearchComparisonPageAPI(ResearchBaseAPI, ResultsPageAPI):

    _FAMILY_ = "Research"
    _TASK_ = ResearchBaseAPI.RESEARCH
    _LAUNCH_ = LaunchFieldsAPI.EVERY
    _COLUMNS_ = ["Status", "UID", "Research", "StartedAt", "Duration", "Artifacts"]

    def __init__(self, *, app) -> None:
        super().__init__(app=app, path="/research/comparison", button="Comparison", icon="bi bi-bar-chart-steps", description="Overlay two or more runs — growth curves and metrics side by side")

    def _actions_(self) -> list:
        return [self._compare_button_()]

    def _compare_button_(self):
        button = super()._compare_button_()
        button.background = "success"
        button.tooltip = "Overlay the growth curves and metrics of the selected runs"
        return button

    @staticmethod
    def _comparable_(produced: list) -> bool:
        return any(item.get("Kind") == "Plot" for item in produced)

    def _row_(self, run: dict, produced: list, fields: dict) -> dict | None:
        if not self._comparable_(produced): return None
        return {**super()._row_(run, produced, fields), "Research": self._research_(run)}

    def _extras_(self) -> list:
        return [html.P("Only runs that stored a plot can be overlaid — a run without one has no curve to draw",
                       className="status-line"), *super()._extras_()]