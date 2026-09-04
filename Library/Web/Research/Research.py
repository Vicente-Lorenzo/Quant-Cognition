from dash import html

from Library.App.V2 import SectionPageAPI
from Library.Web.Research.Launch import EVERY, SYSTEMS, TASKS, launch_callbacks
from Library.Web.Research.Result import ResultPageAPI, ResultsPageAPI, LaunchedResultsPageAPI

RESEARCH = ("Research.Backtesting", "Research.Optimization", "Research.Learning")

class ResearchBaseAPI:

    _ANCHOR_ = "/research"

class ResearchPageAPI(ResearchBaseAPI, SectionPageAPI):

    _FAMILY_ = "Research"

    def __init__(self, *, app) -> None:
        super().__init__(app=app, path="/research", button="Research", icon="bi bi-clipboard-data", description="Backtest, optimize and train — every run in one place")

class ResearchRunPageAPI(ResearchBaseAPI, LaunchedResultsPageAPI):

    _FAMILY_ = "Research"
    _TASK_ = RESEARCH
    _TASKS_ = TASKS
    _SYSTEMS_ = SYSTEMS
    _LAUNCH_ = EVERY
    _COLUMNS_ = ["Status", "UID", "Research", "Retention", "StartedAt", "StoppedAt", "Duration", "Progress", "Artifacts"]

    def __init__(self, *, app) -> None:
        super().__init__(app=app, path="/research/all", button="Journal", icon="bi bi-journal-text", description="Every backtest, optimization and learning run together")

    def _launch_button_(self):
        button = super()._launch_button_()
        button.label = self._icon_("bi bi-play-fill", "Run Research", tint="success")
        button.tooltip = "Configure and dispatch a backtest, optimization or learning run"
        return button

    def _rows_(self) -> list:
        rows = super()._rows_()
        for row, run in zip(rows, self._runs_()):
            row["Research"] = str(run.get("TID") or "").split(".")[-1]
            row["Progress"] = self._percentage_(run)
        return rows

    @staticmethod
    def _percentage_(run: dict) -> str:
        fraction = run.get("Progress")
        if fraction is None: return ""
        return f"{float(fraction) * 100.0:.0f}%"

    _open_launch_, _close_launch_, _submit_launch_ = launch_callbacks(_LAUNCH_)

class ResearchResultPageAPI(ResearchBaseAPI, ResultPageAPI):

    _FAMILY_ = "Result"
    _LAUNCH_ = EVERY

    def __init__(self, *, app) -> None:
        super().__init__(app=app, path="/research/:uid", button="Result", icon="bi bi-clipboard-data", parametric=True)

class ResearchComparisonPageAPI(ResearchBaseAPI, ResultsPageAPI):

    _FAMILY_ = "Research"
    _TASK_ = RESEARCH
    _LAUNCH_ = EVERY
    _COLUMNS_ = ["Status", "UID", "Research", "StartedAt", "Duration", "Artifacts"]

    def __init__(self, *, app) -> None:
        super().__init__(app=app, path="/research/comparison", button="Comparison", icon="bi bi-bar-chart-steps", description="Overlay two or more runs \u2014 growth curves and metrics side by side")

    def _actions_(self) -> list:
        return [self._compare_button_()]

    def _compare_button_(self):
        button = super()._compare_button_()
        button.background = "success"
        button.tooltip = "Overlay the growth curves and metrics of the selected runs"
        return button

    def _comparable_(self, run: dict) -> bool:
        return any(item.get("Kind") == "Plot" for item in self._produced_(run))

    def _rows_(self) -> list:
        keep = []
        for row, run in zip(super()._rows_(), self._runs_()):
            if not self._comparable_(run): continue
            row["Research"] = str(run.get("TID") or "").split(".")[-1]
            keep.append(row)
        return keep

    def _extras_(self) -> list:
        return [html.P("Only runs that stored a plot can be overlaid \u2014 a run without one has no curve to draw",
                       className="status-line"), *super()._extras_()]