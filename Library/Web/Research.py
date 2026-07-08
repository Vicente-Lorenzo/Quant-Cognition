from dash import html

from Library.App.V2 import PageAPI, ContainerAPI, TextAPI

class ResearchPageAPI(PageAPI):

    def __init__(self, *, app) -> None:
        super().__init__(app=app, path="/research", button="Research", icon="bi bi-graph-up-arrow", description="Explore market data securities and indicators across the universe")

    def content(self) -> list:
        return [
            TextAPI(text="Market Research", classname="page-title", builder=html.H1),
            TextAPI(text="Explore market data, securities and indicators across the universe.", classname="page-lead", builder=html.P),
            ContainerAPI(fluid=True, classname="panel", elements=[
                TextAPI(text="Market Data", classname="panel-title", builder=html.H5),
                TextAPI(text="Security browser, price charts and indicator studies coming soon.", builder=html.P),
            ]),
        ]