from __future__ import annotations

import dash
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from Library.App.V2.Core.Callback import Output, Input, State, InjectionType, serverside_callback
from Library.App.V2.Core.Identity import GlobalAPI
from Library.App.V2.Session import TriggerAPI
from Library.Utility.Path import inspect_file, inspect_file_path

if TYPE_CHECKING:
    from Library.App.V2.Page.Page import PageAPI

class RouterAPI(GlobalAPI):

    def resolve(self, *, path: PurePosixPath | str, relative: bool, footer: bool = None) -> str:
        path = inspect_file(path, header=False, builder=PurePosixPath)
        path = self._anchor_ / path if relative else path
        return inspect_file_path(path, header=True, footer=footer, builder=PurePosixPath)

    def anchorize(self, *, path: PurePosixPath | str, relative: bool = True) -> str:
        return self.resolve(path=path, relative=relative, footer=False)

    def endpointize(self, *, path: PurePosixPath | str, relative: bool = True) -> str:
        return self.resolve(path=path, relative=relative, footer=True)

    def locate(self, *, endpoint: str) -> tuple[str, PageAPI | None]:
        page = self._pages_.get(endpoint, None)
        if page is not None: return endpoint, page
        if self._parametrics_: return self._locate_parametric_(endpoint=endpoint)
        return endpoint, None

    def _locate_parametric_(self, *, endpoint: str) -> tuple[str, PageAPI | None]:
        parts = inspect_file(endpoint, header=True, builder=PurePosixPath).parts
        for cut in range(len(parts) - 1, 1, -1):
            entry = self._parametrics_.get(self.endpointize(path=PurePosixPath(*parts[:cut]), relative=False))
            if entry is not None: return endpoint, entry[0]
        return endpoint, None

    def redirect(self, *, endpoint: str) -> tuple[str, PageAPI | None]:
        endpoint, page = self.locate(endpoint=endpoint)
        while page and page.endpoint != page.redirect:
            endpoint, page = self.locate(endpoint=page.redirect)
        return endpoint, page

    def destination(self, page: PageAPI) -> str:
        _, target = self.redirect(endpoint=page.endpoint)
        resolved = target or page
        return resolved.anchor or resolved.endpoint

    def index(self, *, endpoint: str, page: PageAPI) -> None:
        self._pages_[endpoint] = page
        self._log_.debug(lambda: f"Index Operation: Indexed ({endpoint})")

    @serverside_callback(
        Output(GlobalAPI.GLOBAL_LOCATION_ID, "pathname"),
        Output(GlobalAPI.GLOBAL_ROUTING_STORAGE_ID, "data"),
        Output(GlobalAPI.GLOBAL_NAVIGATION_ID, "children"),
        Output(GlobalAPI.GLOBAL_SIDEBAR_ID, "children"),
        Output(GlobalAPI.GLOBAL_CONTENT_ID, "children"),
        Output(GlobalAPI.GLOBAL_ENTER_ASYNC_ID, "data"),
        Output(GlobalAPI.GLOBAL_REENTER_ASYNC_ID, "data"),
        Output(GlobalAPI.GLOBAL_ROUTE_ASYNC_ID, "data"),
        Output(GlobalAPI.GLOBAL_LEAVE_ASYNC_ID, "data"),
        Output(GlobalAPI.GLOBAL_USER_STORAGE_ID, "data"),
        Input(GlobalAPI.GLOBAL_LOCATION_ID, "pathname"),
        State(GlobalAPI.GLOBAL_ROUTING_STORAGE_ID, "data"),
        State(GlobalAPI.GLOBAL_ENTER_ASYNC_ID, "data"),
        State(GlobalAPI.GLOBAL_REENTER_ASYNC_ID, "data"),
        State(GlobalAPI.GLOBAL_ROUTE_ASYNC_ID, "data"),
        State(GlobalAPI.GLOBAL_LEAVE_ASYNC_ID, "data"),
        on_init=InjectionType.Hidden
    )
    def _global_async_update_location_callback_(self, pathname, routing, enter, reenter, route, leave):
        endpoint = self.endpointize(path=pathname, relative=False)
        current = (routing or {}).get("current")
        redirect, page = self.redirect(endpoint=endpoint)
        forbidden, role, account = False, None, dash.no_update
        if self._auth_ is not None:
            from flask_login import current_user
            role = current_user.Role
            account = {"name": current_user.Name or current_user.Username, "role": role.name} if current_user.is_authenticated else None
            if redirect != self._login_ and not current_user.grants(self._required_(page)):
                if current_user.is_authenticated: forbidden = True
                else: redirect, page = self.redirect(endpoint=self._login_)
        enter, reenter, route, leave = TriggerAPI(**(enter or {})), TriggerAPI(**(reenter or {})), TriggerAPI(**(route or {})), TriggerAPI(**(leave or {}))
        if current == redirect:
            enter, reenter, route, leave = dash.no_update, reenter.trigger().dict(), route.trigger().dict(), dash.no_update
            self._log_.debug(lambda: f"Route Operation: Reentered ({redirect})")
        else:
            enter, reenter, route, leave = enter.trigger().dict(), dash.no_update, route.trigger().dict(), leave.trigger().dict()
            self._log_.info(lambda: f"Route Operation: Entered ({redirect})")
        if forbidden:
            navigation, sidebar, content = dash.no_update, self.GLOBAL_FORBIDDEN_LAYOUT, self.GLOBAL_FORBIDDEN_LAYOUT
            self._log_.warning(lambda: f"Access Operation: Denied ({endpoint})")
        elif page:
            navigation = page._navigation_ if page._navigation_ else dash.no_update
            dynamic = page.personalize(role)
            sidebar, content = page._sidebar_, dynamic if dynamic is not None else page._content_
        else:
            navigation, sidebar, content = dash.no_update, self.GLOBAL_NOT_FOUND_LAYOUT, self.GLOBAL_NOT_FOUND_LAYOUT
            self._log_.warning(lambda: f"Route Operation: Missing ({endpoint})")
        if current == redirect and not forbidden and page:
            navigation = sidebar = content = dash.no_update
        normalized = self.anchorize(path=redirect, relative=False) or "/"
        return (normalized if normalized != pathname else dash.no_update), {"current": redirect}, navigation, sidebar, content, enter, reenter, route, leave, account