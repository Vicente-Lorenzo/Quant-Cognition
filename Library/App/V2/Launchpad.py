from dataclasses import dataclass

from dash import html

from Library.App.V2.Component import ButtonAPI, ComponentAPI, ContainerAPI, IconAPI, TextAPI
from Library.App.V2.Page import PageAPI

@dataclass(kw_only=True)
class LinkAPI:

    name: str
    url: str
    icon: str = None
    description: str = None

class LaunchpadPageAPI(PageAPI):

    def __init__(self, *, app) -> None:
        super().__init__(app=app, path="/", button="Launchpad", icon="bi bi-grid-3x3-gap", add_backward_parent=False, add_current_parent=False, add_current_children=True, add_forward_parent=False, add_forward_children=False)
        self._tiles_ = {}
        self._links_ = None
        self._heading_ = TextAPI(text="Launchpad", classname="app-launchpad-title", builder=html.H1)

    def personalize(self, role) -> list:
        return ComponentAPI.flatten([*self.normalize(self._render_(role)), *self.__init_hidden_layout__()])

    def content(self) -> ContainerAPI:
        return self._render_(None)

    def _render_(self, role) -> ContainerAPI:
        if self._links_ is None: self._links_ = [self._link_(link) for link in self.app.apps()]
        tiles = [self._tile_(child, role) for child in self.children if child.button]
        tiles.extend(self._links_)
        grid = ContainerAPI(builder=html.Div, classname="app-launchpad-grid", elements=tiles) if tiles else TextAPI(text="No applications registered", classname="app-launchpad-empty")
        return ContainerAPI(fluid=True, classname="app-launchpad", elements=[self._heading_, grid])

    def _tile_(self, page: PageAPI, role) -> ButtonAPI:
        locked = role is not None and not role.grants(self.app._required_(page))
        key = (page.endpoint, locked)
        tile = self._tiles_.get(key)
        if tile is not None: return tile
        label = [IconAPI(icon=page.icon or "bi bi-app", classname="app-tile-icon"), TextAPI(text=page.button, classname="app-tile-name")]
        if page.description: label.append(TextAPI(text=page.description, classname="app-tile-desc"))
        if locked:
            label.insert(0, IconAPI(icon="bi bi-lock-fill", classname="app-tile-lock"))
            tile = ButtonAPI(background="link", classname="app-tile app-tile-locked", disabled=True, label=label)
        else:
            tile = ButtonAPI(href=page.anchor or page.endpoint, background="link", classname="app-tile", label=label)
        self._tiles_[key] = tile
        return tile

    @staticmethod
    def _link_(link: LinkAPI) -> ButtonAPI:
        label = [IconAPI(icon="bi bi-box-arrow-up-right", classname="app-tile-badge"), IconAPI(icon=link.icon or "bi bi-app", classname="app-tile-icon"), TextAPI(text=link.name, classname="app-tile-name")]
        if link.description: label.append(TextAPI(text=link.description, classname="app-tile-desc"))
        return ButtonAPI(href=link.url, external=True, background="link", classname="app-tile", label=label)