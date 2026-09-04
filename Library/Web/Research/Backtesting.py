from Library.System.System import SystemType

from Library.Web.Research.Launch import launch_callbacks, MARKET, OUTPUT
from Library.Web.Research.Result import LaunchedResultsPageAPI

class BacktestingPageAPI(LaunchedResultsPageAPI):

    _FAMILY_ = "Backtest"
    _SYSTEM_ = SystemType.Backtesting.name
    _TASK_ = "Research.Backtesting"
    _LAUNCH_ = MARKET + OUTPUT
    _ANCHOR_ = "/research"

    def __init__(self, *, app) -> None:
        super().__init__(app=app, path="/research/backtesting", button="Backtesting", icon="bi bi-rewind-circle", description="Launch backtests and review their result views")

    _open_launch_, _close_launch_, _submit_launch_ = launch_callbacks(_LAUNCH_)