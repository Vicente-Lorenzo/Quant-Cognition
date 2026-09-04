from flask import g, request

from Library.App.V2 import AppAPI, LinkAPI, PageAPI
from Library.Auth import AuthAPI, RoleAPI
from Library.Database import PostgresDatabaseAPI
from Library.Utility.Path import traceback_root
from Library.Web.Core import ARTIFACTS
from Library.Web.Launchpad import WebLaunchpadPageAPI
from Library.Web.Trading import TradingPageAPI
from Library.Web.Framework import (
    DatabasePageAPI,
    HierarchyPageAPI,
    FrameworkPageAPI
)
from Library.Web.Strategy import (
    StrategyPageAPI,
    StrategySystemPageAPI,
    StrategyScopePageAPI,
    StrategyStrategyPageAPI
)
from Library.Web.Scheduler import (
    SchedulerPageAPI,
    SchedulerWorkflowPageAPI,
    SchedulerWorkflowDetailPageAPI,
    SchedulerTaskPageAPI,
    SchedulerTaskDetailPageAPI,
    SchedulerRunPageAPI,
    SchedulerRunDetailPageAPI
)
from Library.Web.Research import (
    BacktestingPageAPI,
    OptimizationPageAPI,
    LearningPageAPI,
    ResearchPageAPI,
    ResearchRunPageAPI,
    ResearchResultPageAPI,
    ResearchComparisonPageAPI
)

class WebAppAPI(AppAPI):

    Launchpad = WebLaunchpadPageAPI

    _MOTTOS_ = traceback_root() / "MOTTOS.md"
    _DATABASE_ = "Quant"

    def __init__(self, *, motto: str | list = None, auth: AuthAPI | None = None, access: RoleAPI = RoleAPI.Viewer, **kwargs) -> None:
        super().__init__(motto=motto if motto is not None else self._mottos_(), auth=auth if auth is not None else AuthAPI(), access=access, **kwargs)
        ARTIFACTS.install(self.app.server)
        self._scoped_(self.app.server, self._DATABASE_)

    @staticmethod
    def _scoped_(server, database: str) -> None:
        @server.before_request
        def _open_():
            if request.method != "POST": return None
            g._scope_ = PostgresDatabaseAPI.scope(database=database)
            g._scope_.__enter__()
            return None

        @server.teardown_request
        def _close_(error):
            scope = g.pop("_scope_", None)
            if scope is not None: scope.__exit__(type(error) if error else None, error, None)

    @classmethod
    def _mottos_(cls) -> list:
        try:
            lines = cls._MOTTOS_.read_text(encoding="utf-8").splitlines()
        except OSError:
            return []
        return [line[2:].strip() for line in lines if line.startswith("- ") and line[2:].strip()]

    def _page_(self, page: PageAPI, access: RoleAPI) -> None:
        page.access = access
        self.link(page)

    def pages(self) -> None:
        self._page_(TradingPageAPI(app=self), RoleAPI.Administrator)
        self._page_(ResearchPageAPI(app=self), RoleAPI.Editor)
        self._page_(ResearchRunPageAPI(app=self), RoleAPI.Editor)
        self._page_(BacktestingPageAPI(app=self), RoleAPI.Editor)
        self._page_(OptimizationPageAPI(app=self), RoleAPI.Editor)
        self._page_(LearningPageAPI(app=self), RoleAPI.Editor)
        self._page_(ResearchComparisonPageAPI(app=self), RoleAPI.Editor)
        self._page_(ResearchResultPageAPI(app=self), RoleAPI.Editor)
        self._page_(StrategyPageAPI(app=self), RoleAPI.Editor)
        self._page_(StrategySystemPageAPI(app=self), RoleAPI.Editor)
        self._page_(StrategyScopePageAPI(app=self), RoleAPI.Editor)
        self._page_(StrategyStrategyPageAPI(app=self), RoleAPI.Editor)
        self._page_(SchedulerPageAPI(app=self), RoleAPI.Editor)
        self._page_(SchedulerWorkflowPageAPI(app=self), RoleAPI.Editor)
        self._page_(SchedulerTaskPageAPI(app=self), RoleAPI.Editor)
        self._page_(SchedulerRunPageAPI(app=self), RoleAPI.Editor)
        self._page_(SchedulerWorkflowDetailPageAPI(app=self), RoleAPI.Editor)
        self._page_(SchedulerTaskDetailPageAPI(app=self), RoleAPI.Editor)
        self._page_(SchedulerRunDetailPageAPI(app=self), RoleAPI.Editor)
        self._page_(FrameworkPageAPI(app=self), RoleAPI.Viewer)
        self._page_(DatabasePageAPI(app=self), RoleAPI.Moderator)
        self._page_(HierarchyPageAPI(app=self), RoleAPI.Viewer)

    def apps(self) -> list[LinkAPI]:
        return [
            LinkAPI(name="cTrader", url="https://app.ctrader.com", icon="bi bi-graph-up-arrow", description="Open the cTrader web trading platform"),
            LinkAPI(name="TradingView", url="https://www.tradingview.com/chart", icon="bi bi-bar-chart-line", description="Open TradingView charts in a new tab"),
        ]

if __name__ == "__main__":
    WebAppAPI(name="Quant Cognition", title="Quant Cognition", team="Vicente Lorenzo", contact="vicente.aser.lorenzo@gmail.com", debug=True).run()