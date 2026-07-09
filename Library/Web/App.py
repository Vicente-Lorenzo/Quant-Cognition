from Library.App.V2 import AppAPI, PageAPI
from Library.Auth import AuthAPI
from Library.Web.Live import LivePageAPI
from Library.Web.Database import DatabasePageAPI
from Library.Web.Learning import LearningPageAPI
from Library.Web.Research import ResearchPageAPI
from Library.Web.Hierarchy import HierarchyPageAPI
from Library.Web.Scheduler import SchedulerPageAPI
from Library.Web.Backtesting import BacktestingPageAPI
from Library.Web.Optimization import OptimizationPageAPI

class WebAppAPI(AppAPI):

    def __init__(self, *, motto: str = "In the middle of difficulty lies opportunity", auth: AuthAPI = None, access: str = "Viewer", **kwargs) -> None:
        super().__init__(motto=motto, auth=auth if auth is not None else AuthAPI(), access=access, **kwargs)

    def _page_(self, page: PageAPI, access: str) -> None:
        page.access = access
        self.link(page)

    def pages(self) -> None:
        self._page_(ResearchPageAPI(app=self), "Viewer")
        self._page_(LivePageAPI(app=self), "Administrator")
        self._page_(BacktestingPageAPI(app=self), "Member")
        self._page_(OptimizationPageAPI(app=self), "Member")
        self._page_(LearningPageAPI(app=self), "Member")
        self._page_(DatabasePageAPI(app=self), "Moderator")
        self._page_(HierarchyPageAPI(app=self), "Viewer")
        self._page_(SchedulerPageAPI(app=self), "Member")

    def apps(self) -> list[dict]:
        return [
            {"name": "cTrader", "url": "https://app.ctrader.com", "icon": "bi bi-graph-up-arrow", "description": "Open the cTrader web trading platform"},
            {"name": "TradingView", "url": "https://www.tradingview.com/chart", "icon": "bi bi-bar-chart-line", "description": "Open TradingView charts in a new tab"},
        ]

if __name__ == "__main__":
    WebAppAPI(name="Quant Cognition", title="Quant Cognition", team="Vicente Lorenzo", contact="vicente.aser.lorenzo@gmail.com", debug=True).run()