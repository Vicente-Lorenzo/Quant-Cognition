from Library.System.System import SystemType

from Library.Web.Research.Launch import launch_callbacks, MARKET, OPTIMIZATION, OUTPUT
from Library.Web.Research.Result import LaunchedResultsPageAPI

class OptimizationPageAPI(LaunchedResultsPageAPI):

    _FAMILY_ = "Optimization"
    _SYSTEM_ = SystemType.Optimization.name
    _TASK_ = "Research.Optimization"
    _LAUNCH_ = MARKET + OPTIMIZATION + OUTPUT
    _ANCHOR_ = "/research"

    def __init__(self, *, app) -> None:
        super().__init__(app=app, path="/research/optimization", button="Optimization", icon="bi bi-sliders2", description="Search the parameter space and review the elected configuration")

    _open_launch_, _close_launch_, _submit_launch_ = launch_callbacks(_LAUNCH_)