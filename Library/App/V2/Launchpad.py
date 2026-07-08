from dash import html

from Library.App.V2.Component import ButtonAPI, ColContainerAPI, ContainerAPI, IconAPI, RowContainerAPI, TextAPI
from Library.App.V2.Page import PageAPI

class LaunchpadPageAPI(PageAPI):

    def __init__(self, *, app) -> None:
        super().__init__(app=app, path="/", button="Launchpad", icon="bi bi-grid-3x3-gap", add_backward_parent=False, add_current_parent=False, add_current_children=True, add_forward_parent=False, add_forward_children=False)

    def content(self) -> ContainerAPI:
        tiles = [self._tile_(child) for child in self.children if child.button]
        grid = RowContainerAPI(classname="app-launchpad-grid", elements=tiles) if tiles else TextAPI(text="No applications registered", classname="app-launchpad-empty")
        heading = TextAPI(text="Applications", classname="app-launchpad-title", builder=html.H1)
        return ContainerAPI(fluid=True, classname="app-launchpad", elements=[heading, grid])

    @staticmethod
    def _tile_(page: PageAPI) -> ColContainerAPI:
        label = [IconAPI(icon=page.icon or "bi bi-app", classname="app-tile-icon"), TextAPI(text=page.button, classname="app-tile-name")]
        if page.description: label.append(TextAPI(text=page.description, classname="app-tile-desc"))
        return ColContainerAPI(classname="app-tile-col", width={"xs": 12, "sm": 6, "md": 4, "lg": 3}, elements=[ButtonAPI(href=page.endpoint, background="link", classname="app-tile", label=label)])