from typing import Union, Generic
from typing_extensions import Self

from Library.App.V1 import AppType
from Library.Logging import LoggingAPI
from Library.App.V1.Component import Component, StorageAPI
from Library.App.V1.Callback import ComponentID, Output, Input, InjectionType, clientside_callback, serverside_callback

class PageAPI(Generic[AppType]):

    PAGE_ENTER_ASYNC_ID: Union[ComponentID, dict] = ComponentID()
    PAGE_REENTER_ASYNC_ID: Union[ComponentID, dict] = ComponentID()
    PAGE_ROUTE_ASYNC_ID: Union[ComponentID, dict] = ComponentID()
    PAGE_LEAVE_ASYNC_ID: Union[ComponentID, dict] = ComponentID()

    PAGE_MEMORY_STORAGE_ID: Union[ComponentID, dict] = ComponentID()
    PAGE_SESSION_STORAGE_ID: Union[ComponentID, dict] = ComponentID()
    PAGE_LOCAL_STORAGE_ID: Union[ComponentID, dict] = ComponentID()

    def __init__(self, *,
                 app: AppType,
                 path: str,
                 anchor: str = None,
                 endpoint: str = None,
                 redirect: str = None,
                 button: str = None,
                 description: str = None,
                 content: Union[Component, list[Component]] = None,
                 sidebar: Union[Component, list[Component]] = None,
                 navigation: Union[Component, list[Component]] = None,
                 add_backward_parent: bool = True,
                 add_backward_children: bool = False,
                 add_current_parent: bool = False,
                 add_current_children: bool = True,
                 add_forward_parent: bool = False,
                 add_forward_children: bool = True) -> None:

        self._log_ = LoggingAPI()

        self.app: AppType = app
        self.path: str = path
        self.button: str = button
        self.description: str = description

        self._add_backward_parent_: bool = add_backward_parent
        self._add_backward_children_: bool = add_backward_children
        self._add_current_parent_: bool = add_current_parent
        self._add_current_children_: bool = add_current_children
        self._add_forward_parent_: bool = add_forward_parent
        self._add_forward_children_: bool = add_forward_children

        self._anchor_: str = self.app.anchorize(path=anchor, relative=True) if anchor else anchor
        self._endpoint_: str = self.app.endpointize(path=endpoint, relative=True) if endpoint else endpoint
        self._redirect_: str = self.app.endpointize(path=redirect, relative=True) if redirect else redirect

        self._sidebar_: list[Component] = self.normalize(sidebar)
        self._content_: list[Component] = self.normalize(content)
        self._navigation_: list[Component] = self.normalize(navigation)

        self._parent_: Union[PageAPI, None] = None
        self._children_: list[PageAPI] = []

        self._initialized_: bool = False

    @staticmethod
    def normalize(element: Union[Component, list[Component]]) -> list[Component]:
        if element is None: return []
        return [element] if isinstance(element, Component) else list(element)

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
        if parent is None:
            return
        if self._parent_ is parent:
            return
        if self._parent_:
            self._parent_._children_.remove(self)
        self._parent_ = parent
        if self in parent._children_:
            idx = parent._children_.index(self)
            parent._children_[idx] = self
        else:
            parent._children_.append(self)
        self._log_.info(lambda: f"Attached {parent} (Parent) to {self} (Child)")

    def merge(self, page: Self) -> None:
        parent = page._parent_
        self._parent_ = parent
        if parent:
            idx = parent._children_.index(page)
            parent._children_[idx] = self
        self._children_ = list(page._children_)
        for child in self._children_:
            child._parent_ = self
        page._parent_ = None
        page._children_.clear()
        self._log_.info(lambda: f"Merged {page} (Old) into {self} (New)")

    @clientside_callback(
        Output(PAGE_MEMORY_STORAGE_ID, "data"),
        on_clean_memory=InjectionType.Hidden
    )
    def _page_async_clean_memory_callback_(self):
        return self.app.asset(path="Callbacks/Clear.js", url=False)

    @clientside_callback(
        Output(PAGE_SESSION_STORAGE_ID, "data"),
        on_clean_session=InjectionType.Hidden
    )
    def _page_async_clean_session_callback_(self):
        return self.app.asset(path="Callbacks/Clear.js", url=False)

    @clientside_callback(
        Output(PAGE_LOCAL_STORAGE_ID, "data"),
        on_clean_local=InjectionType.Hidden
    )
    def _page_async_clean_local_callback_(self):
        return self.app.asset(path="Callbacks/Clear.js", url=False)

    @serverside_callback(
        Input(PAGE_MEMORY_STORAGE_ID, "data")
    )
    def _page_async_update_memory_callback_(self, data):
        self._log_.info(lambda: f"Page Memory Storage: {data if data else 'Empty'}")
        if not data: self.app._injector_.on_clean_memory.increment()

    @serverside_callback(
        Input(PAGE_SESSION_STORAGE_ID, "data")
    )
    def _page_async_update_session_callback_(self, data):
        self._log_.info(lambda: f"Page Session Storage: {data if data else 'Empty'}")
        if not data: self.app._injector_.on_clean_session.increment()

    @serverside_callback(
        Input(PAGE_LOCAL_STORAGE_ID, "data")
    )
    def _page_async_update_local_callback_(self, data):
        self._log_.info(lambda: f"Page Local Storage: {data if data else 'Empty'}")
        if not data: self.app._injector_.on_clean_local.increment()

    def __init_ids__(self) -> None:
        self.PAGE_ENTER_ASYNC_ID: dict = self.register(type="asyncer", name="enter")
        self.PAGE_REENTER_ASYNC_ID: dict = self.register(type="asyncer", name="reenter")
        self.PAGE_ROUTE_ASYNC_ID: dict = self.register(type="asyncer", name="route")
        self.PAGE_LEAVE_ASYNC_ID: dict = self.register(type="asyncer", name="leave")

        self.PAGE_MEMORY_STORAGE_ID: dict = self.register(type="storage", name="memory", portable="data")
        self.PAGE_SESSION_STORAGE_ID: dict = self.register(type="storage", name="session", portable="data")
        self.PAGE_LOCAL_STORAGE_ID: dict = self.register(type="storage", name="local", portable="data")
        self.ids()

    def __init_hidden_layout__(self) -> list[Component]:
        hidden: list = []
        hidden.extend(StorageAPI(id=self.PAGE_ENTER_ASYNC_ID, persistence="memory").build())
        hidden.extend(StorageAPI(id=self.PAGE_REENTER_ASYNC_ID, persistence="memory").build())
        hidden.extend(StorageAPI(id=self.PAGE_ROUTE_ASYNC_ID, persistence="memory").build())
        hidden.extend(StorageAPI(id=self.PAGE_LEAVE_ASYNC_ID, persistence="memory").build())
        hidden.extend(StorageAPI(id=self.PAGE_MEMORY_STORAGE_ID, persistence="memory").build())
        hidden.extend(StorageAPI(id=self.PAGE_SESSION_STORAGE_ID, persistence="session").build())
        hidden.extend(StorageAPI(id=self.PAGE_LOCAL_STORAGE_ID, persistence="local").build())
        return self.normalize(hidden)

    def __init_content_layout__(self) -> list[Component]:
        hidden = self.__init_hidden_layout__()
        self._log_.debug(lambda: f"Loaded Hidden Layout")
        content = self.normalize(self._content_ or self.content())
        return self.normalize([*content, *hidden])

    def __init_sidebar_layout__(self) -> list[Component]:
        sidebar = self.normalize(self._sidebar_ or self.sidebar())
        return self.normalize([*sidebar])

    def __init_navigation_layout__(self) -> list[Component]:
        navigation = self.normalize(self._navigation_ or self.navigation())
        return self.normalize([*navigation])

    def _init_layout_(self) -> None:
        self._content_ = self.__init_content_layout__()
        self._log_.debug(lambda: f"Loaded Content Layout")
        self._sidebar_ = self.__init_sidebar_layout__()
        self._log_.debug(lambda: f"Loaded Sidebar Layout")
        self._navigation_ = self.__init_navigation_layout__()
        self._log_.debug(lambda: f"Loaded Navigation Layout")

    def _init_(self) -> None:
        if self._initialized_: return
        self.__init_ids__()
        self._log_.info(lambda: f"Initialized IDs: {self}")
        self._init_layout_()
        self._log_.info(lambda: f"Initialized Layout: {self}")
        self._initialized_ = True

    def ids(self) -> None:
        """
        Override this method to register custom Dash IDs.
        """
        pass

    def content(self) -> Union[Component, list[Component]]:
        """
        Override this method to provide the page content.
        """
        return self.normalize(self.app.GLOBAL_NOT_INDEXED_LAYOUT)

    def sidebar(self) -> Union[Component, list[Component]]:
        """
        Override this method to provide the page sidebar.
        """
        return self.normalize(self.app.GLOBAL_NOT_INDEXED_LAYOUT)

    def navigation(self) -> Union[Component, list[Component]]:
        """
        Override this method to provide the page navigation.
        """
        pass

    def __repr__(self) -> str:
        return repr(f"{self.description} @ {self.endpoint}")