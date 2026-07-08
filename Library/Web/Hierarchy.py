from dash import html

from Library.App.V2 import PageAPI, ContainerAPI, TextAPI

class HierarchyPageAPI(PageAPI):

    def __init__(self, *, app) -> None:
        super().__init__(app=app, path="/hierarchy", button="Hierarchy", icon="bi bi-diagram-3", description="Explore the module hierarchy and dependency graph of a library")

    def content(self) -> list:
        return [
            TextAPI(text="Module Hierarchy", classname="page-title", builder=html.H1),
            TextAPI(text="Visualize and interact with a library's module dependency graph.", classname="page-lead", builder=html.P),
            ContainerAPI(fluid=True, classname="panel", elements=[
                TextAPI(text="Dependency Graph", classname="panel-title", builder=html.H5),
                TextAPI(text="Interactive dependency graph powered by networkx coming soon.", builder=html.P),
            ]),
        ]