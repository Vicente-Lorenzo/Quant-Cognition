from Library.App.V2 import AppAPI
from Library.Web.Live import LivePageAPI
from Library.Web.Database import DatabasePageAPI
from Library.Web.Learning import LearningPageAPI
from Library.Web.Research import ResearchPageAPI
from Library.Web.Hierarchy import HierarchyPageAPI
from Library.Web.Scheduler import SchedulerPageAPI
from Library.Web.Backtesting import BacktestingPageAPI
from Library.Web.Optimization import OptimizationPageAPI

class WebAppAPI(AppAPI):

    def __init__(self, *, motto: str = "In the middle of difficulty lies opportunity", **kwargs) -> None:
        super().__init__(motto=motto, **kwargs)

    def pages(self) -> None:
        self.link(ResearchPageAPI(app=self))
        self.link(LivePageAPI(app=self))
        self.link(BacktestingPageAPI(app=self))
        self.link(OptimizationPageAPI(app=self))
        self.link(LearningPageAPI(app=self))
        self.link(DatabasePageAPI(app=self))
        self.link(HierarchyPageAPI(app=self))
        self.link(SchedulerPageAPI(app=self))

if __name__ == "__main__":
    WebAppAPI(name="Quant Cognition", title="Quant Cognition", team="Vicente Lorenzo", debug=True).run()