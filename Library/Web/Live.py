from dash import html

from Library.App.V2 import PageAPI, ContainerAPI, TextAPI

class LivePageAPI(PageAPI):

    def __init__(self, *, app) -> None:
        super().__init__(app=app, path="/live", button="Live", icon="bi bi-broadcast", description="Monitor and control live trading strategies in real time")

    def content(self) -> list:
        return [
            TextAPI(text="Live Trading", classname="page-title", builder=html.H1),
            TextAPI(text="Monitor and control live trading strategies in real time.", classname="page-lead", builder=html.P),
            ContainerAPI(fluid=True, classname="panel", elements=[
                TextAPI(text="Active Strategies", classname="panel-title", builder=html.H5),
                TextAPI(text="No strategies running. Live positions, orders and account monitoring coming soon.", builder=html.P),
            ]),
        ]