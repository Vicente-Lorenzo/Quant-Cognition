from dash import html

from Library.App.V2.Component import ButtonAPI, ContainerAPI, IconAPI, TextAPI
from Library.App.V2.Page import PageAPI

class LaunchpadPageAPI(PageAPI):

    def __init__(self, *, app) -> None:
        super().__init__(app=app, path="/", button="Launchpad", icon="bi bi-grid-3x3-gap", add_backward_parent=False, add_current_parent=False, add_current_children=True, add_forward_parent=False, add_forward_children=False)

    def content(self) -> ContainerAPI:
        tiles = [self._tile_(child) for child in self.children if child.button]
        tiles.extend(self._link_(app) for app in self.app.apps())
        grid = ContainerAPI(builder=html.Div, classname="app-launchpad-grid", elements=tiles) if tiles else TextAPI(text="No applications registered", classname="app-launchpad-empty")
        heading = TextAPI(text="Launchpad", classname="app-launchpad-title", builder=html.H1)
        return ContainerAPI(fluid=True, classname="app-launchpad", elements=[heading, grid])

    @staticmethod
    def _tile_(page: PageAPI) -> ButtonAPI:
        label = [IconAPI(icon=page.icon or "bi bi-app", classname="app-tile-icon"), TextAPI(text=page.button, classname="app-tile-name")]
        if page.description: label.append(TextAPI(text=page.description, classname="app-tile-desc"))
        return ButtonAPI(href=page.endpoint, background="link", classname="app-tile", label=label)

    @staticmethod
    def _link_(app: dict) -> ButtonAPI:
        label = [IconAPI(icon="bi bi-box-arrow-up-right", classname="app-tile-badge"), IconAPI(icon=app.get("icon") or "bi bi-app", classname="app-tile-icon"), TextAPI(text=app["name"], classname="app-tile-name")]
        if app.get("description"): label.append(TextAPI(text=app["description"], classname="app-tile-desc"))
        return ButtonAPI(href=app["url"], external=True, background="link", classname="app-tile", label=label)