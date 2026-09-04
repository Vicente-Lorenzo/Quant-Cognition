from Library.System.System import SystemType

from Library.Web.Research.Launch import launch_callbacks, MARKET, LEARNING, OUTPUT
from Library.Web.Research.Result import LaunchedResultsPageAPI

class LearningPageAPI(LaunchedResultsPageAPI):

    _FAMILY_ = "Learning"
    _SYSTEM_ = SystemType.Learning.name
    _TASK_ = "Research.Learning"
    _LAUNCH_ = MARKET + LEARNING + OUTPUT
    _ANCHOR_ = "/research"

    def __init__(self, *, app) -> None:
        super().__init__(app=app, path="/research/learning", button="Learning", icon="bi bi-robot", description="Train agents and review their weights and result views")

    _open_launch_, _close_launch_, _submit_launch_ = launch_callbacks(_LAUNCH_)