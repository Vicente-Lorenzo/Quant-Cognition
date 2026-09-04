from dataclasses import dataclass

from dash import html

from Library.App.V2.Component.Component import ButtonAPI, ComponentAPI, ContainerAPI, IconAPI, TextAPI
from Library.App.V2.Page.Page import PageAPI

@dataclass(kw_only=True)
class LinkAPI:

    name: str
    url: str
    icon: str = None
    description: str = None

class LaunchpadAPI:

    _EXTERNAL_ = False

    def _launchpad_(self, role=None) -> ContainerAPI:
        tiles = [self._tile_(child, role) for child in self.children if child.button and not child._parametric_]
        if self._EXTERNAL_: tiles.extend(self._link_(link) for link in self.app.apps())
        heading = TextAPI(text=self.button, classname="app-launchpad-title", builder=html.H1)
        grid = ContainerAPI(builder=html.Div, classname="app-launchpad-grid", elements=tiles) if tiles else TextAPI(text="No applications registered", classname="app-launchpad-empty")
        return ContainerAPI(fluid=True, classname="app-launchpad", elements=[heading, grid])

    def _tile_(self, page: PageAPI, role) -> ButtonAPI:
        locked = role is not None and not role.grants(self.app._required_(page))
        label = [IconAPI(icon=page.icon or "bi bi-app", classname="app-tile-icon"), TextAPI(text=page.button, classname="app-tile-name")]
        if page.description: label.append(TextAPI(text=page.description, classname="app-tile-desc"))
        if locked:
            label.insert(0, IconAPI(icon="bi bi-lock-fill", classname="app-tile-lock"))
            return ButtonAPI(background="link", classname="app-tile app-tile-locked", disabled=True, label=label)
        return ButtonAPI(href=self.app.destination(page), background="link", classname="app-tile", label=label)

    @staticmethod
    def _link_(link: LinkAPI) -> ButtonAPI:
        label = [IconAPI(icon="bi bi-box-arrow-up-right", classname="app-tile-badge"), IconAPI(icon=link.icon or "bi bi-app", classname="app-tile-icon"), TextAPI(text=link.name, classname="app-tile-name")]
        if link.description: label.append(TextAPI(text=link.description, classname="app-tile-desc"))
        return ButtonAPI(href=link.url, external=True, background="link", classname="app-tile", label=label)

class SectionPageAPI(LaunchpadAPI, PageAPI):

    def personalize(self, role) -> list:
        return ComponentAPI.flatten([*self.normalize(self._launchpad_(role)), *self.__init_hidden_layout__()])

    def content(self) -> ContainerAPI:
        return self._launchpad_(None)

class LaunchpadPageAPI(SectionPageAPI):

    _EXTERNAL_ = True

    def __init__(self, *, app) -> None:
        super().__init__(app=app, path="/", button="Launchpad", icon="bi bi-grid-3x3-gap", add_backward_parent=False, add_current_parent=False, add_current_children=True, add_forward_parent=False, add_forward_children=False)