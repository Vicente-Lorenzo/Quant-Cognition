import threading
from abc import ABC, abstractmethod
from dash.exceptions import PreventUpdate
from typing import Union, Callable, Tuple, Any

from Library.App.V1.Session import TriggerAPI
from Library.App.V1.Callback import Input, Output, State, InjectionType

class InjectionAPI(ABC):
    def __init__(self, flag: str, default: InjectionType):
        self.flag = flag
        self.default = default
        self.mapping: dict[str, int] = {}
        self.counter: int = 0
        self.index: int = 0
        self.lock: threading.RLock = threading.RLock()
    @abstractmethod
    def args(self, is_page: bool) -> list:
        pass
    @staticmethod
    def py(payload: dict) -> Any:
        return None
    @staticmethod
    def js(app) -> Union[str, None]:
        return None
    @staticmethod
    def running() -> list[tuple]:
        return []
    @staticmethod
    def cancel() -> list[Any]:
        return []
    def __call__(self, app, is_page: bool) -> Tuple[Union[Callable, None], str | None]:
        return self.py, self.js(app)
    def register(self, page: str = None) -> None:
        with self.lock:
            self.counter += 1
            key = page or "global"
            self.mapping[key] = self.mapping.get(key, 0) + 1
    def increment(self) -> None:
        with self.lock:
            self.index += 1
    def reset(self) -> None:
        with self.lock:
            self.index = 0
    def count(self, app: bool = True, page: Union[bool, str] = False) -> int:
        with self.lock:
            total = 0
            if app:
                total += self.mapping.get("global", 0)
            if isinstance(page, str):
                total += self.mapping.get(page, 0)
            elif page:
                total += sum(v for k, v in self.mapping.items() if k != "global")
            return total

class OnClickInjectionAPI(InjectionAPI):
    def __init__(self):
        super().__init__(flag="on_click", default=InjectionType.Hidden)
    def args(self, is_page: bool) -> list:
        return []
    def py(self, payload: dict) -> Any:
        original_inputs = payload.get("original_inputs", [])
        clicks = original_inputs[0] if original_inputs else None
        if not clicks: raise PreventUpdate
    def js(self, app) -> str:
        return app.asset(path="Callbacks/Click.js", url=False)

class OnCleanInjectionAPI(InjectionAPI, ABC):
    def py(self, payload: dict) -> Any:
        injected_inputs = payload.get("injected_inputs", [])
        clicks = injected_inputs[0] if len(injected_inputs) > 0 else None
        trigger = injected_inputs[1] if len(injected_inputs) > 1 else None
        if not clicks and not trigger: raise PreventUpdate
    def js(self, app) -> str:
        return app.asset(path="Callbacks/Clean.js", url=False)

class OnCleanMemoryInjectionAPI(OnCleanInjectionAPI):
    def __init__(self):
        super().__init__(flag="on_clean_memory", default=InjectionType.Hidden)
    def args(self, is_page: bool) -> list:
        from Library.App.V1 import AppAPI
        return [Input(AppAPI.GLOBAL_CLEAN_MEMORY_BUTTON_ID, "n_clicks"),
                Input(AppAPI.GLOBAL_CLEAN_MEMORY_ASYNC_ID, "data")]

class OnCleanSessionInjectionAPI(OnCleanInjectionAPI):
    def __init__(self):
        super().__init__(flag="on_clean_session", default=InjectionType.Hidden)
    def args(self, is_page: bool) -> list:
        from Library.App.V1 import AppAPI
        return [Input(AppAPI.GLOBAL_CLEAN_SESSION_BUTTON_ID, "n_clicks"),
                Input(AppAPI.GLOBAL_CLEAN_SESSION_ASYNC_ID, "data")]

class OnCleanLocalInjectionAPI(OnCleanInjectionAPI):
    def __init__(self):
        super().__init__(flag="on_clean_local", default=InjectionType.Hidden)
    def args(self, is_page: bool) -> list:
        from Library.App.V1 import AppAPI
        return [Input(AppAPI.GLOBAL_CLEAN_LOCAL_BUTTON_ID, "n_clicks"),
                Input(AppAPI.GLOBAL_CLEAN_LOCAL_ASYNC_ID, "data")]

class OnCleanResetInjectionAPI(OnCleanInjectionAPI):
    def __init__(self):
        super().__init__(flag="on_clean_reset", default=InjectionType.Hidden)
    def args(self, is_page: bool) -> list:
        from Library.App.V1 import AppAPI
        return [Input(AppAPI.GLOBAL_CLEAN_RESET_BUTTON_ID, "n_clicks"),
                Input(AppAPI.GLOBAL_CLEAN_RESET_ASYNC_ID, "data")]

class OnSyncInjectionAPI(InjectionAPI, ABC):
    def py(self, payload: dict) -> Any:
        injected_inputs = payload.get("injected_inputs", [])
        trigger = injected_inputs[0] if injected_inputs else None
        if not trigger: raise PreventUpdate
        return TriggerAPI(**trigger).trigger().dict()
    def js(self, app) -> str:
        return app.asset(path="Callbacks/Trigger.js", url=False)
    def __call__(self, app, is_page: bool) -> Tuple[Union[Callable, None], str | None]:
        return (self.py, self.js(app)) if is_page else (None, None)

class OnEnterInjectionAPI(OnSyncInjectionAPI):
    def __init__(self):
        super().__init__(flag="on_enter", default=InjectionType.Hidden)
    def args(self, is_page: bool) -> list:
        from Library.App.V1 import AppAPI, PageAPI
        if is_page:
            return [Output(PageAPI.PAGE_ENTER_ASYNC_ID, "data"),
                    Input(AppAPI.GLOBAL_ENTER_ASYNC_ID, "data"),
                    State(PageAPI.PAGE_ENTER_ASYNC_ID, "data")]
        return [Input(AppAPI.GLOBAL_ENTER_ASYNC_ID, "data")]

class OnReenterInjectionAPI(OnSyncInjectionAPI):
    def __init__(self):
        super().__init__(flag="on_reenter", default=InjectionType.Hidden)
    def args(self, is_page: bool) -> list:
        from Library.App.V1 import AppAPI, PageAPI
        if is_page:
            return [Output(PageAPI.PAGE_REENTER_ASYNC_ID, "data"),
                    Input(AppAPI.GLOBAL_REENTER_ASYNC_ID, "data"),
                    State(PageAPI.PAGE_REENTER_ASYNC_ID, "data")]
        return [Input(AppAPI.GLOBAL_REENTER_ASYNC_ID, "data")]

class OnRouteInjectionAPI(OnSyncInjectionAPI):
    def __init__(self):
        super().__init__(flag="on_route", default=InjectionType.Hidden)
    def args(self, is_page: bool) -> list:
        from Library.App.V1 import AppAPI, PageAPI
        if is_page:
            return [Output(PageAPI.PAGE_ROUTE_ASYNC_ID, "data"),
                    Input(AppAPI.GLOBAL_ROUTE_ASYNC_ID, "data"),
                    State(PageAPI.PAGE_ROUTE_ASYNC_ID, "data")]
        return [Input(AppAPI.GLOBAL_ROUTE_ASYNC_ID, "data")]

class OnLeaveInjectionAPI(OnSyncInjectionAPI):
    def __init__(self):
        super().__init__(flag="on_leave", default=InjectionType.Hidden)
    def args(self, is_page: bool) -> list:
        from Library.App.V1 import AppAPI, PageAPI
        if is_page:
            return [Output(PageAPI.PAGE_LEAVE_ASYNC_ID, "data"),
                    Input(AppAPI.GLOBAL_LEAVE_ASYNC_ID, "data"),
                    State(PageAPI.PAGE_LEAVE_ASYNC_ID, "data")]
        return [Input(AppAPI.GLOBAL_LEAVE_ASYNC_ID, "data")]

class LoadingInjectionAPI(InjectionAPI):
    def __init__(self):
        super().__init__(flag="loading", default=InjectionType.Hidden)
    def args(self, is_page: bool) -> list: return []
    def running(self) -> list[tuple]:
        from Library.App.V1 import AppAPI
        return [(Output(AppAPI.GLOBAL_CONTENT_LOADING_ID, "style"), {"display": "flex"}, {"display": "none"}),
                (Output(AppAPI.GLOBAL_SIDEBAR_LOADING_ID, "style"), {"display": "flex"}, {"display": "none"})]

class LoadingContentInjectionAPI(InjectionAPI):
    def __init__(self):
        super().__init__(flag="loading_content", default=InjectionType.Hidden)
    def args(self, is_page: bool) -> list: return []
    def running(self) -> list[tuple]:
        from Library.App.V1 import AppAPI
        return [(Output(AppAPI.GLOBAL_CONTENT_LOADING_ID, "style"), {"display": "flex"}, {"display": "none"})]

class LoadingSidebarInjectionAPI(InjectionAPI):
    def __init__(self):
        super().__init__(flag="loading_sidebar", default=InjectionType.Hidden)
    def args(self, is_page: bool) -> list: return []
    def running(self) -> list[tuple]:
        from Library.App.V1 import AppAPI
        return [(Output(AppAPI.GLOBAL_SIDEBAR_LOADING_ID, "style"), {"display": "flex"}, {"display": "none"})]

class EmailInjectionAPI(InjectionAPI):
    def __init__(self):
        super().__init__(flag="email", default=InjectionType.Append)
    def args(self, is_page: bool) -> list:
        from Library.App.V1 import AppAPI
        return [Output(AppAPI.GLOBAL_EMAIL_STORAGE_ID, "data")]

class InjectorAPI:
    def __init__(self, app):
        self.app = app
        self.on_click = OnClickInjectionAPI()
        self.on_clean_memory = OnCleanMemoryInjectionAPI()
        self.on_clean_session = OnCleanSessionInjectionAPI()
        self.on_clean_local = OnCleanLocalInjectionAPI()
        self.on_clean_reset = OnCleanResetInjectionAPI()
        self.on_enter = OnEnterInjectionAPI()
        self.on_reenter = OnReenterInjectionAPI()
        self.on_route = OnRouteInjectionAPI()
        self.on_leave = OnLeaveInjectionAPI()
        self.loading = LoadingInjectionAPI()
        self.loading_content = LoadingContentInjectionAPI()
        self.loading_sidebar = LoadingSidebarInjectionAPI()
        self.email = EmailInjectionAPI()
        self.injections = [
            self.on_click,
            self.on_clean_memory,
            self.on_clean_session,
            self.on_clean_local,
            self.on_clean_reset,
            self.on_enter,
            self.on_reenter,
            self.on_route,
            self.on_leave,
            self.loading,
            self.loading_content,
            self.loading_sidebar,
            self.email
        ]
    def match(self, func) -> list[InjectionAPI]:
        matched = []
        for inj in self.injections:
            mode = getattr(func, inj.flag, False)
            mode = InjectionType.coerce(mode)
            if mode is not InjectionType.Disabled:
                matched.append(inj)
        return matched