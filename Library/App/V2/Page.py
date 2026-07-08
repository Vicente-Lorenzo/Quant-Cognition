from typing import Generic
from typing_extensions import Self

from Library.App.V2 import AppType
from Library.App.V2.Component import Component, ComponentAPI, StorageAPI
from Library.App.V2.Callback import ComponentID
from Library.Logging import HandlerLoggingAPI

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
                 content: Component | list[Component] = None,
                 sidebar: Component | list[Component] = None,
                 navigation: Component | list[Component] = None,
                 add_backward_parent: bool = True,
                 add_backward_children: bool = False,
                 add_current_parent: bool = False,
                 add_current_children: bool = True,
                 add_forward_parent: bool = False,
                 add_forward_children: bool = True) -> None:
        self._log_ = HandlerLoggingAPI(Class=self.__class__.__name__, Subclass="Page Management")
        self.app = app
        self.path = path
        self.button = button
        self.icon = icon
        self.description = description
        self._add_backward_parent_ = add_backward_parent
        self._add_backward_children_ = add_backward_children
        self._add_current_parent_ = add_current_parent
        self._add_current_children_ = add_current_children
        self._add_forward_parent_ = add_forward_parent
        self._add_forward_children_ = add_forward_children
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

    def identify(self, *, page: str = None, type: str, name: str, portable: str = "", **kwargs) -> dict:
        page = page or self.endpoint or "global"
        return self.app.identify(page=page, type=type, name=name, portable=portable, **kwargs)

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

    def content(self) -> Component | list[Component]:
        return self.normalize(self.app.GLOBAL_DEVELOPMENT_LAYOUT)

    def sidebar(self) -> Component | list[Component]:
        return []

    def navigation(self) -> Component | list[Component]:
        return []

    def __repr__(self) -> str:
        return repr(f"{self.button or self.__class__.__name__} @ {self.endpoint}")