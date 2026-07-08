from Library.Web.Launcher import LauncherPageAPI

class OptimizationPageAPI(LauncherPageAPI):

    def __init__(self, *, app) -> None:
        super().__init__(app=app, path="/optimization", button="Optimization", icon="bi bi-sliders2", step="Optimization", action="Run Optimization", description="Search the parameter space and review the best configurations")