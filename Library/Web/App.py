from Library.App.V2 import AppAPI, LinkAPI, PageAPI
from Library.Auth import AuthAPI, RoleAPI
from Library.Utility.Path import traceback_root
from Library.Web.Live import LivePageAPI
from Library.Web.Database import DatabasePageAPI
from Library.Web.Learning import LearningPageAPI
from Library.Web.Research import ResearchPageAPI
from Library.Web.Hierarchy import HierarchyPageAPI
from Library.Web.Scheduler import SchedulerPageAPI, SchedulerWorkflowsPageAPI, SchedulerWorkflowDetailPageAPI, SchedulerTasksPageAPI, SchedulerTaskDetailPageAPI, SchedulerRunsPageAPI, SchedulerRunDetailPageAPI
from Library.Web.Backtesting import BacktestingPageAPI
from Library.Web.Optimization import OptimizationPageAPI

class WebAppAPI(AppAPI):

    _MOTTOS_ = traceback_root() / "MOTTOS.md"

    def __init__(self, *, motto: str | list = None, auth: AuthAPI | None = None, access: RoleAPI = RoleAPI.Viewer, **kwargs) -> None:
        super().__init__(motto=motto if motto is not None else self._mottos_(), auth=auth if auth is not None else AuthAPI(), access=access, **kwargs)

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
        self._page_(ResearchPageAPI(app=self), RoleAPI.Viewer)
        self._page_(LivePageAPI(app=self), RoleAPI.Administrator)
        self._page_(BacktestingPageAPI(app=self), RoleAPI.Editor)
        self._page_(OptimizationPageAPI(app=self), RoleAPI.Editor)
        self._page_(LearningPageAPI(app=self), RoleAPI.Editor)
        self._page_(DatabasePageAPI(app=self), RoleAPI.Moderator)
        self._page_(HierarchyPageAPI(app=self), RoleAPI.Viewer)
        self._page_(SchedulerPageAPI(app=self), RoleAPI.Editor)
        self._page_(SchedulerWorkflowsPageAPI(app=self), RoleAPI.Editor)
        self._page_(SchedulerTasksPageAPI(app=self), RoleAPI.Editor)
        self._page_(SchedulerRunsPageAPI(app=self), RoleAPI.Editor)
        self._page_(SchedulerWorkflowDetailPageAPI(app=self), RoleAPI.Editor)
        self._page_(SchedulerTaskDetailPageAPI(app=self), RoleAPI.Editor)
        self._page_(SchedulerRunDetailPageAPI(app=self), RoleAPI.Editor)

    def apps(self) -> list[LinkAPI]:
        return [
            LinkAPI(name="cTrader", url="https://app.ctrader.com", icon="bi bi-graph-up-arrow", description="Open the cTrader web trading platform"),
            LinkAPI(name="TradingView", url="https://www.tradingview.com/chart", icon="bi bi-bar-chart-line", description="Open TradingView charts in a new tab"),
        ]

if __name__ == "__main__":
    WebAppAPI(name="Quant Cognition", title="Quant Cognition", team="Vicente Lorenzo", contact="vicente.aser.lorenzo@gmail.com", debug=True).run()