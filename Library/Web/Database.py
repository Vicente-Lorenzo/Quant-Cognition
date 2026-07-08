from dash import html

from Library.App.V2 import PageAPI, ContainerAPI, TextAPI

class DatabasePageAPI(PageAPI):

    def __init__(self, *, app) -> None:
        super().__init__(app=app, path="/database", button="Database", icon="bi bi-database", description="Browse and edit database tables across the universe schema")

    def content(self) -> list:
        return [
            TextAPI(text="Database", classname="page-title", builder=html.H1),
            TextAPI(text="Browse and edit database tables across the universe schema.", classname="page-lead", builder=html.P),
            ContainerAPI(fluid=True, classname="panel", elements=[
                TextAPI(text="Tables", classname="panel-title", builder=html.H5),
                TextAPI(text="Table browser with inline editing coming soon.", builder=html.P),
            ]),
        ]