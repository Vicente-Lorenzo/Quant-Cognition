from __future__ import annotations

from abc import ABC
from typing import Any, Callable

from dash.exceptions import PreventUpdate

from Library.App.V2.Callback import Input, Output, State, InjectionType
from Library.App.V2.Session import TriggerAPI

class InjectionAPI(ABC):

    def __init__(self, flag: str, default: InjectionType) -> None:
        self.flag = flag
        self.default = default

    def args(self, is_page: bool) -> list:
        return []

    def pre(self, app, is_page: bool) -> Callable | None:
        return None

    def post(self, app, is_page: bool) -> Callable | None:
        return None

    def pre_js(self, app, is_page: bool) -> str | None:
        return None

    def post_js(self, app, is_page: bool) -> str | None:
        return None

    def running(self) -> list[tuple]:
        return []

    def cancel(self) -> list[Any]:
        return []

    def spec(self, app, is_page: bool, mode: InjectionType) -> dict:
        return {"mode": mode, "args": self.args(is_page), "pre": self.pre(app, is_page), "post": self.post(app, is_page), "pre_js": self.pre_js(app, is_page), "post_js": self.post_js(app, is_page)}

class OnClickInjectionAPI(InjectionAPI):

    def __init__(self) -> None:
        super().__init__(flag="on_click", default=InjectionType.Hidden)

    def pre(self, app, is_page: bool) -> Callable:
        return self._guard_

    def pre_js(self, app, is_page: bool) -> str:
        return app.asset("Callbacks/Click.js", url=False)

    @staticmethod
    def _guard_(payload: dict) -> None:
        clicks = payload["original_inputs"][0] if payload["original_inputs"] else None
        if not clicks: raise PreventUpdate

class OnCleanInjectionAPI(InjectionAPI, ABC):

    def pre(self, app, is_page: bool) -> Callable:
        return self._guard_

    def pre_js(self, app, is_page: bool) -> str:
        return app.asset("Callbacks/Clean.js", url=False)

    @staticmethod
    def _guard_(payload: dict) -> None:
        injected = payload["injected_inputs"]
        clicks = injected[0] if len(injected) > 0 else None
        trigger = injected[1] if len(injected) > 1 else None
        if not clicks and not trigger: raise PreventUpdate

class OnCleanMemoryInjectionAPI(OnCleanInjectionAPI):

    def __init__(self) -> None:
        super().__init__(flag="on_clean_memory", default=InjectionType.Hidden)

    def args(self, is_page: bool) -> list:
        from Library.App.V2 import AppAPI
        return [Input(AppAPI.GLOBAL_CLEAN_MEMORY_BUTTON_ID, "n_clicks"), Input(AppAPI.GLOBAL_CLEAN_MEMORY_ASYNC_ID, "data")]

class OnCleanSessionInjectionAPI(OnCleanInjectionAPI):

    def __init__(self) -> None:
        super().__init__(flag="on_clean_session", default=InjectionType.Hidden)

    def args(self, is_page: bool) -> list:
        from Library.App.V2 import AppAPI
        return [Input(AppAPI.GLOBAL_CLEAN_SESSION_BUTTON_ID, "n_clicks"), Input(AppAPI.GLOBAL_CLEAN_SESSION_ASYNC_ID, "data")]

class OnCleanLocalInjectionAPI(OnCleanInjectionAPI):

    def __init__(self) -> None:
        super().__init__(flag="on_clean_local", default=InjectionType.Hidden)

    def args(self, is_page: bool) -> list:
        from Library.App.V2 import AppAPI
        return [Input(AppAPI.GLOBAL_CLEAN_LOCAL_BUTTON_ID, "n_clicks"), Input(AppAPI.GLOBAL_CLEAN_LOCAL_ASYNC_ID, "data")]

class OnCleanResetInjectionAPI(OnCleanInjectionAPI):

    def __init__(self) -> None:
        super().__init__(flag="on_clean_reset", default=InjectionType.Hidden)

    def args(self, is_page: bool) -> list:
        from Library.App.V2 import AppAPI
        return [Input(AppAPI.GLOBAL_CLEAN_RESET_BUTTON_ID, "n_clicks"), Input(AppAPI.GLOBAL_CLEAN_RESET_ASYNC_ID, "data")]

class OnSyncInjectionAPI(InjectionAPI, ABC):

    def pre(self, app, is_page: bool) -> Callable | None:
        return self._trigger_ if is_page else None

    def pre_js(self, app, is_page: bool) -> str | None:
        return app.asset("Callbacks/Trigger.js", url=False) if is_page else None

    @staticmethod
    def _trigger_(payload: dict) -> Any:
        injected = payload["injected_inputs"]
        trigger = injected[0] if injected else None
        if not trigger: raise PreventUpdate
        return TriggerAPI(**trigger).trigger().dict()

class OnEnterInjectionAPI(OnSyncInjectionAPI):

    def __init__(self) -> None:
        super().__init__(flag="on_enter", default=InjectionType.Hidden)

    def args(self, is_page: bool) -> list:
        from Library.App.V2 import AppAPI, PageAPI
        if is_page:
            return [Output(PageAPI.PAGE_ENTER_ASYNC_ID, "data"), Input(AppAPI.GLOBAL_ENTER_ASYNC_ID, "data"), State(PageAPI.PAGE_ENTER_ASYNC_ID, "data")]
        return [Input(AppAPI.GLOBAL_ENTER_ASYNC_ID, "data")]

class OnReenterInjectionAPI(OnSyncInjectionAPI):

    def __init__(self) -> None:
        super().__init__(flag="on_reenter", default=InjectionType.Hidden)

    def args(self, is_page: bool) -> list:
        from Library.App.V2 import AppAPI, PageAPI
        if is_page:
            return [Output(PageAPI.PAGE_REENTER_ASYNC_ID, "data"), Input(AppAPI.GLOBAL_REENTER_ASYNC_ID, "data"), State(PageAPI.PAGE_REENTER_ASYNC_ID, "data")]
        return [Input(AppAPI.GLOBAL_REENTER_ASYNC_ID, "data")]

class OnRouteInjectionAPI(OnSyncInjectionAPI):

    def __init__(self) -> None:
        super().__init__(flag="on_route", default=InjectionType.Hidden)

    def args(self, is_page: bool) -> list:
        from Library.App.V2 import AppAPI, PageAPI
        if is_page:
            return [Output(PageAPI.PAGE_ROUTE_ASYNC_ID, "data"), Input(AppAPI.GLOBAL_ROUTE_ASYNC_ID, "data"), State(PageAPI.PAGE_ROUTE_ASYNC_ID, "data")]
        return [Input(AppAPI.GLOBAL_ROUTE_ASYNC_ID, "data")]

class OnLeaveInjectionAPI(OnSyncInjectionAPI):

    def __init__(self) -> None:
        super().__init__(flag="on_leave", default=InjectionType.Hidden)

    def args(self, is_page: bool) -> list:
        from Library.App.V2 import AppAPI, PageAPI
        if is_page:
            return [Output(PageAPI.PAGE_LEAVE_ASYNC_ID, "data"), Input(AppAPI.GLOBAL_LEAVE_ASYNC_ID, "data"), State(PageAPI.PAGE_LEAVE_ASYNC_ID, "data")]
        return [Input(AppAPI.GLOBAL_LEAVE_ASYNC_ID, "data")]

class OnLoadingInjectionAPI(InjectionAPI):

    def __init__(self) -> None:
        super().__init__(flag="on_loading", default=InjectionType.Hidden)

    def running(self) -> list[tuple]:
        from Library.App.V2 import AppAPI
        return [(Output(AppAPI.GLOBAL_CONTENT_LOADING_ID, "style"), {"display": "flex"}, {"display": "none"}), (Output(AppAPI.GLOBAL_SIDEBAR_LOADING_ID, "style"), {"display": "flex"}, {"display": "none"})]

class OnLoadingContentInjectionAPI(InjectionAPI):

    def __init__(self) -> None:
        super().__init__(flag="on_loading_content", default=InjectionType.Hidden)

    def running(self) -> list[tuple]:
        from Library.App.V2 import AppAPI
        return [(Output(AppAPI.GLOBAL_CONTENT_LOADING_ID, "style"), {"display": "flex"}, {"display": "none"})]

class OnLoadingSidebarInjectionAPI(InjectionAPI):

    def __init__(self) -> None:
        super().__init__(flag="on_loading_sidebar", default=InjectionType.Hidden)

    def running(self) -> list[tuple]:
        from Library.App.V2 import AppAPI
        return [(Output(AppAPI.GLOBAL_SIDEBAR_LOADING_ID, "style"), {"display": "flex"}, {"display": "none"})]

class OnEmailInjectionAPI(InjectionAPI):

    def __init__(self) -> None:
        super().__init__(flag="on_email", default=InjectionType.Append)

    def args(self, is_page: bool) -> list:
        from Library.App.V2 import AppAPI
        return [Output(AppAPI.GLOBAL_EMAIL_STORAGE_ID, "data")]

    def post(self, app, is_page: bool) -> Callable:
        return self._email_

    def post_js(self, app, is_page: bool) -> str:
        return app.asset("Callbacks/Email.js", url=False)

    @staticmethod
    def _email_(payload: dict) -> Any:
        outputs = payload["original_outputs"]
        return outputs[0] if outputs else None

class InjectorAPI:

    def __init__(self, app) -> None:
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
        self.on_loading = OnLoadingInjectionAPI()
        self.on_loading_content = OnLoadingContentInjectionAPI()
        self.on_loading_sidebar = OnLoadingSidebarInjectionAPI()
        self.on_email = OnEmailInjectionAPI()
        self.injections = [self.on_click, self.on_clean_memory, self.on_clean_session, self.on_clean_local, self.on_clean_reset, self.on_enter, self.on_reenter, self.on_route, self.on_leave, self.on_loading, self.on_loading_content, self.on_loading_sidebar, self.on_email]

    def match(self, func) -> list[InjectionAPI]:
        matched = []
        for injection in self.injections:
            mode = InjectionType.coerce(getattr(func, injection.flag, False))
            if mode is not InjectionType.Disabled: matched.append(injection)
        return matched