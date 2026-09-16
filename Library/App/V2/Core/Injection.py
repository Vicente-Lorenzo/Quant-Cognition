from abc import ABC
from typing import Any, Callable
from dash.exceptions import PreventUpdate

from Library.App.V2.Core.Callback import ComponentID, Input, Output, State, InjectionType
from Library.App.V2.Core.Identity import GlobalAPI
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
        if not any(payload["original_inputs"] or ()): raise PreventUpdate

class OnCleanInjectionAPI(InjectionAPI):

    def __init__(self, flag: str, button: ComponentID, asyncer: ComponentID) -> None:
        super().__init__(flag=flag, default=InjectionType.Hidden)
        self.button = button
        self.asyncer = asyncer

    def args(self, is_page: bool) -> list:
        return [Input(self.button, "n_clicks"), Input(self.asyncer, "data")]

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

class OnSyncInjectionAPI(InjectionAPI):

    def __init__(self, flag: str, source: ComponentID, target: ComponentID) -> None:
        super().__init__(flag=flag, default=InjectionType.Hidden)
        self.source = source
        self.target = target

    def args(self, is_page: bool) -> list:
        if is_page: return [Output(self.target, "data"), Input(self.source, "data"), State(self.target, "data")]
        return [Input(self.source, "data")]

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

class OnLoadingInjectionAPI(InjectionAPI):

    def __init__(self, flag: str, *loadings: ComponentID) -> None:
        super().__init__(flag=flag, default=InjectionType.Hidden)
        self.loadings = loadings

    def running(self) -> list[tuple]:
        return [(Output(loading, "style"), {"display": "flex"}, {"display": "none"}) for loading in self.loadings]

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
        from Library.App.V2.Page.Page import PageAPI
        self.app = app
        self.on_click = OnClickInjectionAPI()
        self.on_clean_memory = OnCleanInjectionAPI("on_clean_memory", GlobalAPI.GLOBAL_CLEAN_MEMORY_BUTTON_ID, GlobalAPI.GLOBAL_CLEAN_MEMORY_ASYNC_ID)
        self.on_clean_session = OnCleanInjectionAPI("on_clean_session", GlobalAPI.GLOBAL_CLEAN_SESSION_BUTTON_ID, GlobalAPI.GLOBAL_CLEAN_SESSION_ASYNC_ID)
        self.on_clean_local = OnCleanInjectionAPI("on_clean_local", GlobalAPI.GLOBAL_CLEAN_LOCAL_BUTTON_ID, GlobalAPI.GLOBAL_CLEAN_LOCAL_ASYNC_ID)
        self.on_clean_reset = OnCleanInjectionAPI("on_clean_reset", GlobalAPI.GLOBAL_CLEAN_RESET_BUTTON_ID, GlobalAPI.GLOBAL_CLEAN_RESET_ASYNC_ID)
        self.on_enter = OnSyncInjectionAPI("on_enter", GlobalAPI.GLOBAL_ENTER_ASYNC_ID, PageAPI.PAGE_ENTER_ASYNC_ID)
        self.on_reenter = OnSyncInjectionAPI("on_reenter", GlobalAPI.GLOBAL_REENTER_ASYNC_ID, PageAPI.PAGE_REENTER_ASYNC_ID)
        self.on_route = OnSyncInjectionAPI("on_route", GlobalAPI.GLOBAL_ROUTE_ASYNC_ID, PageAPI.PAGE_ROUTE_ASYNC_ID)
        self.on_leave = OnSyncInjectionAPI("on_leave", GlobalAPI.GLOBAL_LEAVE_ASYNC_ID, PageAPI.PAGE_LEAVE_ASYNC_ID)
        self.on_loading = OnLoadingInjectionAPI("on_loading", GlobalAPI.GLOBAL_CONTENT_LOADING_ID, GlobalAPI.GLOBAL_SIDEBAR_LOADING_ID)
        self.on_loading_content = OnLoadingInjectionAPI("on_loading_content", GlobalAPI.GLOBAL_CONTENT_LOADING_ID)
        self.on_loading_sidebar = OnLoadingInjectionAPI("on_loading_sidebar", GlobalAPI.GLOBAL_SIDEBAR_LOADING_ID)
        self.on_email = OnEmailInjectionAPI()
        self.injections = [self.on_click, self.on_clean_memory, self.on_clean_session, self.on_clean_local, self.on_clean_reset, self.on_enter, self.on_reenter, self.on_route, self.on_leave, self.on_loading, self.on_loading_content, self.on_loading_sidebar, self.on_email]

    def match(self, func) -> list[InjectionAPI]:
        matched = []
        for injection in self.injections:
            mode = InjectionType.coerce(getattr(func, injection.flag, False))
            if mode is not InjectionType.Disabled: matched.append(injection)
        return matched