from Library.Web.Launcher import LauncherPageAPI

class BacktestingPageAPI(LauncherPageAPI):

    def __init__(self, *, app) -> None:
        super().__init__(app=app, path="/backtesting", button="Backtesting", icon="bi bi-rewind-circle", step="Backtesting", action="Run Backtest", description="Configure and launch a backtest then review its results")