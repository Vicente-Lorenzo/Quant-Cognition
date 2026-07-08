from dash import html

from Library.App.V2 import PageAPI, ContainerAPI, TextAPI

class SchedulerPageAPI(PageAPI):

    def __init__(self, *, app) -> None:
        super().__init__(app=app, path="/scheduler", button="Scheduler", icon="bi bi-calendar2-week", description="Schedule and monitor backtests, optimizations and learning runs")

    def content(self) -> list:
        return [
            TextAPI(text="Scheduled Tasks", classname="page-title", builder=html.H1),
            TextAPI(text="Schedule and monitor backtests, optimizations and learning runs.", classname="page-lead", builder=html.P),
            ContainerAPI(fluid=True, classname="panel", elements=[
                TextAPI(text="Queue", classname="panel-title", builder=html.H5),
                TextAPI(text="No tasks scheduled. Task scheduling and monitoring coming soon.", builder=html.P),
            ]),
        ]