import uuid
from typing import Generic
from typing_extensions import Self

import dash
from dash import html
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate

from Library.App.V2 import AppType
from Library.App.V2.Component.Component import Component, ComponentAPI, ButtonAPI, IconAPI, IntervalAPI, StorageAPI, SwitchAPI, TextAPI
from Library.App.V2.Core.Callback import ComponentID, Output, Input, State, InjectionType, serverside_callback
from Library.Logging import LoggingAPI

class PageAPI(Generic[AppType]):

    PAGE_ENTER_ASYNC_ID: ComponentID | dict = ComponentID()
    PAGE_REENTER_ASYNC_ID: ComponentID | dict = ComponentID()
    PAGE_ROUTE_ASYNC_ID: ComponentID | dict = ComponentID()
    PAGE_LEAVE_ASYNC_ID: ComponentID | dict = ComponentID()

    def __init__(self, *,
                 app: AppType,
                 path: str,
                 anchor: str = None,
                 endpoint: str = None,
                 redirect: str = None,
                 button: str = None,
                 icon: str = None,
                 description: str = None,
                 access: str | int = None,
                 content: Component | list[Component] = None,
                 sidebar: Component | list[Component] = None,
                 navigation: Component | list[Component] = None,
                 add_backward_parent: bool = True,
                 add_backward_children: bool = False,
                 add_current_parent: bool = False,
                 add_current_children: bool = True,
                 add_forward_parent: bool = False,
                 add_forward_children: bool = True,
                 parametric: bool = False) -> None:
        self._log_ = LoggingAPI("Page Management")
        self.app = app
        self.path = path
        self.button = button
        self.icon = icon
        self.description = description
        self.access = access
        self._add_backward_parent_ = add_backward_parent
        self._add_backward_children_ = add_backward_children
        self._add_current_parent_ = add_current_parent
        self._add_current_children_ = add_current_children
        self._add_forward_parent_ = add_forward_parent
        self._add_forward_children_ = add_forward_children
        self._parametric_ = parametric
        self._param_ = None
        self._anchor_ = self.app.anchorize(path=anchor, relative=True) if anchor else anchor
        self._endpoint_ = self.app.endpointize(path=endpoint, relative=True) if endpoint else endpoint
        self._redirect_ = self.app.endpointize(path=redirect, relative=True) if redirect else redirect
        self._sidebar_ = self.normalize(sidebar)
        self._content_ = self.normalize(content)
        self._navigation_ = self.normalize(navigation)
        self._parent_ = None
        self._children_ = []
        self._initialized_ = False

    @staticmethod
    def normalize(element: Component | list[Component]) -> list[Component]:
        if element is None: return []
        return list(element) if isinstance(element, (tuple, list)) else [element]

    @staticmethod
    def _icon_(name: str, label: str = None, tint: str = None) -> list[ComponentAPI]:
        parts = [IconAPI(icon=name, classname=f"icon icon-{tint}") if tint else IconAPI(icon=name)]
        if label is not None: parts.append(TextAPI(text=label))
        return parts

    @staticmethod
    def toolbar(buttons: list, classname: str = "table-toolbar") -> Component:
        built = []
        for button in buttons: built.extend(button.build() if isinstance(button, ComponentAPI) else [button])
        return html.Div(built, className=classname)

    def identify(self, *, page: str = None, type: str, name: str, portable: str = "", **kwargs) -> dict:
        page = page or self.endpoint or "global"
        return self.app.identify(page=page, type=type, name=name, portable=portable, **kwargs)

    def _help_(self, help: str) -> list:
        self._helps_ = getattr(self, "_helps_", 0) + 1
        identifier = self.register(type="icon", name=f"help-{self._helps_}")
        return IconAPI(id=identifier, icon="bi bi-question-circle", classname="app-help", tooltip=help, placement="right").build()

    def _field_(self, label: str, control, help: str = None) -> html.Div:
        caption = [dbc.Label(label)]
        if help: caption += self._help_(help)
        control = control if isinstance(control, list) else [control]
        return html.Div([html.Div(caption, className="app-field-label"), *control], className="app-field")

    def _switch_(self, id: dict, label: str, value, help: str) -> html.Div:
        return html.Div([*SwitchAPI(id=id, label=label, value=value).build(), *self._help_(help)], className="app-switch-field")

    def register(self, *, page: str = None, type: str, name: str, portable: str = "", **kwargs) -> dict:
        page = page or self.endpoint or "global"
        return self.app.register(page=page, type=type, name=name, portable=portable, **kwargs)

    @property
    def anchor(self) -> str:
        return self._anchor_

    @anchor.setter
    def anchor(self, anchor: str) -> None:
        self._anchor_ = self._anchor_ or anchor

    @property
    def endpoint(self) -> str:
        return self._endpoint_

    @endpoint.setter
    def endpoint(self, endpoint: str) -> None:
        self._endpoint_ = self._endpoint_ or endpoint

    @property
    def redirect(self) -> str:
        return self._redirect_ or self.endpoint

    @property
    def parent(self) -> Self:
        return self._parent_

    @property
    def children(self) -> list[Self]:
        return self._children_

    @property
    def family(self) -> list[Self]:
        return [self] + self.children

    def backwards(self) -> list[Self]:
        if not self.parent: return []
        if self._add_backward_parent_: return self.parent.family if self._add_backward_children_ else [self.parent]
        else: return self.parent.children if self._add_backward_children_ else []

    def currents(self) -> list[Self]:
        if self._add_current_parent_: return self.family if self._add_current_children_ else [self]
        else: return self.children if self._add_current_children_ else []

    def forwards(self, current: Self) -> list[Self]:
        if self._add_forward_parent_: return current.family if self._add_forward_children_ else [current]
        else: return current.children if self._add_forward_children_ else []

    def attach(self, parent: Self) -> None:
        if parent is None: return
        if self._parent_ is parent: return
        if self._parent_: self._parent_._children_.remove(self)
        self._parent_ = parent
        if self in parent._children_:
            index = parent._children_.index(self)
            parent._children_[index] = self
        else:
            parent._children_.append(self)
        self._log_.debug(lambda: f"Attach Operation: Attached ({self.endpoint}) · Parent {parent.endpoint}")

    def merge(self, page: Self) -> None:
        parent = page._parent_
        self._parent_ = parent
        if parent:
            index = parent._children_.index(page)
            parent._children_[index] = self
        self._children_ = list(page._children_)
        for child in self._children_: child._parent_ = self
        page._parent_ = None
        page._children_.clear()
        self._log_.debug(lambda: f"Merge Operation: Merged ({self.endpoint}) · From {page.endpoint}")

    def __init_ids__(self) -> None:
        self.PAGE_ENTER_ASYNC_ID = self.register(type="asyncer", name="enter")
        self.PAGE_REENTER_ASYNC_ID = self.register(type="asyncer", name="reenter")
        self.PAGE_ROUTE_ASYNC_ID = self.register(type="asyncer", name="route")
        self.PAGE_LEAVE_ASYNC_ID = self.register(type="asyncer", name="leave")
        self.ids()

    def __init_hidden_layout__(self) -> list[Component]:
        hidden = []
        hidden.extend(StorageAPI(id=self.PAGE_ENTER_ASYNC_ID, persistence="memory").build())
        hidden.extend(StorageAPI(id=self.PAGE_REENTER_ASYNC_ID, persistence="memory").build())
        hidden.extend(StorageAPI(id=self.PAGE_ROUTE_ASYNC_ID, persistence="memory").build())
        hidden.extend(StorageAPI(id=self.PAGE_LEAVE_ASYNC_ID, persistence="memory").build())
        return hidden

    def __init_content_layout__(self) -> list[Component]:
        hidden = self.__init_hidden_layout__()
        content = self._content_ or self.normalize(self.content())
        return ComponentAPI.flatten([*content, *hidden])

    def __init_sidebar_layout__(self) -> list[Component]:
        sidebar = self._sidebar_ or self.normalize(self.sidebar())
        return ComponentAPI.flatten([*sidebar])

    def __init_navigation_layout__(self) -> list[Component]:
        navigation = self._navigation_ or self.normalize(self.navigation())
        return ComponentAPI.flatten([*navigation])

    def _init_layout_(self) -> None:
        self._content_ = self.__init_content_layout__()
        self._sidebar_ = self.__init_sidebar_layout__()
        self._navigation_ = self.__init_navigation_layout__()
        self._log_.debug(lambda: f"Layout Operation: Composed ({self.endpoint})")

    def _init_(self) -> None:
        if self._initialized_: return
        self.__init_ids__()
        self._init_layout_()
        self._initialized_ = True
        self._log_.debug(lambda: f"Build Operation: Built ({self.endpoint})")

    def refresh(self) -> None:
        self._content_, self._sidebar_, self._navigation_ = [], [], []
        self._init_layout_()

    def ids(self) -> None:
        pass

    def personalize(self, role) -> list[Component] | None:
        return None

    def content(self) -> Component | list[Component]:
        return self.normalize(self.app.GLOBAL_DEVELOPMENT_LAYOUT)

    def sidebar(self) -> Component | list[Component]:
        return []

    def navigation(self) -> Component | list[Component]:
        return []

    def __repr__(self) -> str:
        return repr(f"{self.button or self.__class__.__name__} @ {self.endpoint}")

class RefreshAPI:

    RELOAD_STORE_ID: ComponentID | dict = ComponentID()
    FINGERPRINT_STORE_ID: ComponentID | dict = ComponentID()
    INTERVAL_ID: ComponentID | dict = ComponentID()
    REFRESH_BTN: ComponentID | dict = ComponentID()

    _POLL_ = 10000

    def _refresh_ids_(self) -> None:
        self.RELOAD_STORE_ID = self.register(type="store", name="reload")
        self.FINGERPRINT_STORE_ID = self.register(type="store", name="fingerprint")
        self.INTERVAL_ID = self.register(type="interval", name="poll")
        self.REFRESH_BTN = self.register(type="button", name="refresh")

    def _fingerprint_(self):
        return None

    def _refresh_button_(self) -> ButtonAPI:
        return ButtonAPI(id=self.REFRESH_BTN, label=self._icon_("bi bi-arrow-clockwise", "Refresh"), background="secondary", tooltip="Reload from the database")

    def _polling_(self, poll: bool = True) -> list[Component]:
        elements = [StorageAPI(id=self.RELOAD_STORE_ID, data=None), StorageAPI(id=self.FINGERPRINT_STORE_ID, data=None)]
        if poll and self._POLL_: elements.append(IntervalAPI(id=self.INTERVAL_ID, interval=self._POLL_, intervals=0))
        return elements

    @serverside_callback(
        Output(RELOAD_STORE_ID, "data"),
        Output(FINGERPRINT_STORE_ID, "data"),
        on_enter=InjectionType.Hidden,
    )
    def _enter_(self):
        return uuid.uuid4().hex, (self._fingerprint_() or dash.no_update)

    @serverside_callback(
        Output(RELOAD_STORE_ID, "data"),
        Input(REFRESH_BTN, "n_clicks"),
        on_click=InjectionType.Hidden,
    )
    def _refresh_(self, clicks):
        return uuid.uuid4().hex

    @serverside_callback(
        Output(RELOAD_STORE_ID, "data"),
        Output(FINGERPRINT_STORE_ID, "data"),
        Input(INTERVAL_ID, "n_intervals"),
        State(FINGERPRINT_STORE_ID, "data"),
    )
    def _tick_(self, intervals, previous):
        if not intervals: raise PreventUpdate
        token = self._fingerprint_()
        if token is not None and token == previous: raise PreventUpdate
        return uuid.uuid4().hex, (dash.no_update if token is None else token)