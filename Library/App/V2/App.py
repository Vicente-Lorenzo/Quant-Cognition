from __future__ import annotations

import random
import inspect
from typing import TYPE_CHECKING
from pathlib import Path, PurePosixPath

import dash
import flask
import dash_bootstrap_components as dbc
from fastapi import FastAPI
from fastapi.middleware.wsgi import WSGIMiddleware

from Library.App.V2.Core.Callback import Output, Input, State, Trigger, InjectionType, serverside_callback, clientside_callback, inject_serverside, inject_clientside
from Library.App.V2.Core.Identity import GlobalAPI
from Library.App.V2.Core.Shell import ShellAPI
from Library.App.V2.Core.Router import RouterAPI
from Library.App.V2.Component.Component import Component
from Library.App.V2.Core.Injection import InjectorAPI
from Library.App.V2.Component.Notification import NotifierAPI
from Library.App.V2.Page.Page import PageAPI
from Library.App.V2.Page.Launchpad import LinkAPI, LaunchpadPageAPI
from Library.App.V2.Page.Login import LoginPageAPI
from Library.App.V2.Page.Settings import SettingsPageAPI
from Library.Logging import LoggingAPI
from Library.Utility.Path import inspect_file, inspect_file_path, inspect_module, traceback_current_module
from Library.Utility.Runtime import find_host_port
from Library.Utility.Typing import MISSING, getmro, iscallable

if TYPE_CHECKING: from Library.Auth import AuthAPI

class AppAPI(ShellAPI, RouterAPI):

    Theme = [dbc.themes.BOOTSTRAP, dbc.icons.BOOTSTRAP]
    Launchpad: type = LaunchpadPageAPI
    Assets = traceback_current_module(resolve=True) / "Assets"
    _APPLICATION_ = "/_application"
    _META_ = [{"name": "viewport", "content": "width=device-width, initial-scale=1, viewport-fit=cover"},
              {"name": "color-scheme", "content": "light dark"}]

    GLOBAL_NOT_FOUND_LAYOUT: Component
    GLOBAL_LOADING_LAYOUT: Component
    GLOBAL_MAINTENANCE_LAYOUT: Component
    GLOBAL_DEVELOPMENT_LAYOUT: Component
    GLOBAL_FORBIDDEN_LAYOUT: Component

    def __init__(self, *,
                 name: str = "App",
                 title: str = MISSING,
                 team: str = MISSING,
                 contact: str = MISSING,
                 motto: str | list = MISSING,
                 auth: AuthAPI | None = None,
                 access: str | int | None = None,
                 host: str = "127.0.0.1",
                 port: int = MISSING,
                 anchor: str = "/",
                 debug: bool = False) -> None:
        self._log_ = LoggingAPI("App Management")
        self._name_ = name
        self._title_ = title if title is not MISSING else name
        self._team_ = team if team is not MISSING else None
        self._contact_ = contact if contact is not MISSING else None
        self._mottos_ = [] if motto is MISSING or motto is None else [motto] if isinstance(motto, str) else list(motto)
        self._auth_ = auth
        self._access_ = access
        self._host_ = host
        self._port_ = port if port is not MISSING else find_host_port(host=host, port_min=8050)
        self._debug_ = debug
        self._anchor_ = inspect_file(anchor, header=True, builder=PurePosixPath)
        self._endpoint_ = inspect_file_path(anchor, header=True, footer=True, builder=PurePosixPath)
        self._login_ = self.endpointize(path="/login", relative=True)
        self._ids_ = set()
        self._pages_ = {}
        self._parametrics_ = {}
        self._assets_ = inspect_module(inspect.getfile(type(self)), resolve=True) / "Assets"
        self.app = self._compose_()
        if self._auth_ is not None: self._auth_.install(self.app.server, login=self.anchorize(path="/login", relative=True))
        self._log_.debug(lambda: f"Assets Operation: Resolved ({'Application' if self._assets_ != self.Assets else 'Library'})")
        self._injector_ = InjectorAPI(self)
        self._init_ids_()
        self.notify = NotifierAPI(self.GLOBAL_NOTIFICATION_ID)
        self._init_layout_()
        self._init_pages_()
        self._init_navigation_()
        self._init_callbacks_()
        self._log_.info(lambda: f"Build Operation: Built ({self._name_}) · {len(self._pages_)} Pages")

    @staticmethod
    def _read_(path: Path) -> str:
        if path.suffix.lower() in (".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".webp"):
            import base64
            suffix = path.suffix.lower().strip(".")
            mime = {"jpg": "jpeg", "svg": "svg+xml"}.get(suffix, suffix)
            return f"data:image/{mime};base64,{base64.b64encode(path.read_bytes()).decode('utf-8')}"
        return path.read_text(encoding="utf-8")

    def identify(self, *, page: str = None, type: str, name: str, portable: str = "", **kwargs) -> dict:
        page = page or "global"
        return dict(sorted({"app": self.__class__.__name__, "page": page, "type": type, "name": name, "portable": portable, **kwargs}.items()))

    def register(self, *, page: str = "global", type: str, name: str, portable: str = "", **kwargs) -> dict:
        cid = self.identify(page=page, type=type, name=name, portable=portable, **kwargs)
        key = (cid["app"], cid["page"], cid["type"], cid["name"], cid["portable"])
        if key in self._ids_: raise RuntimeError(f"Register Operation: Failed · Due to Duplicate Id ({cid})")
        self._ids_.add(key)
        return cid


    def link(self, page: PageAPI) -> None:
        relative_path = inspect_file(page.path, header=True, builder=PurePosixPath)
        relative_anchor = self.anchorize(path=relative_path, relative=True)
        relative_endpoint = self.endpointize(path=relative_path, relative=True)
        intermediate_alias = inspect_file("/", builder=PurePosixPath)
        _, intermediate_parent = self.locate(endpoint=self.endpointize(path=intermediate_alias, relative=True))
        for part in relative_path.parts[1:-1]:
            intermediate_alias /= inspect_file(part, header=True, builder=PurePosixPath).name
            intermediate_endpoint = self.endpointize(path=intermediate_alias, relative=True)
            _, intermediate_page = self.locate(endpoint=intermediate_endpoint)
            if not intermediate_page:
                intermediate_page = PageAPI(app=self, path=str(intermediate_alias), button=intermediate_alias.name.title(), add_backward_parent=True, add_backward_children=False, add_current_parent=False, add_current_children=False, add_forward_parent=False, add_forward_children=False)
            intermediate_page.anchor = self.anchorize(path=intermediate_alias, relative=True)
            intermediate_page.endpoint = intermediate_endpoint
            intermediate_page._init_()
            self.index(endpoint=intermediate_page.endpoint, page=intermediate_page)
            intermediate_page.attach(parent=intermediate_parent)
            intermediate_parent = intermediate_page
        if page._parametric_:
            page.anchor = relative_anchor
            page.endpoint = relative_endpoint
            page._param_ = relative_path.name.lstrip(":")
            self._parametrics_[intermediate_parent.endpoint] = (page, page._param_)
            self.index(endpoint=page.endpoint, page=page)
            page.attach(parent=intermediate_parent)
            page._init_()
            self._log_.info(lambda: f"Link Operation: Linked ({page.endpoint}) · Parametric ({page._param_})")
            return
        page.anchor = relative_anchor
        page.endpoint = relative_endpoint
        _, existing = self.locate(endpoint=relative_endpoint)
        if existing:
            page.merge(existing)
        else:
            self.index(endpoint=page.endpoint, page=page)
            self._log_.info(lambda: f"Link Operation: Linked ({page.endpoint})")
        page.attach(parent=intermediate_parent)
        page._init_()

    def _serve_(self, app: dash.Dash) -> None:
        assets = self._assets_
        def _view_(filename): return flask.send_from_directory(assets, filename)
        app.server.add_url_rule(f"{self._APPLICATION_}/<path:filename>", endpoint=f"application_{id(self)}", view_func=_view_)

    def _compose_(self) -> dash.Dash:
        overlay = self._assets_.exists() and self._assets_ != self.Assets
        if not overlay: self._assets_ = self.Assets
        external = list(self.Theme)
        if overlay: external += [f"{self._APPLICATION_}/{sheet.relative_to(self._assets_).as_posix()}" for sheet in sorted(self._assets_.rglob("*.css"))]
        app = dash.Dash(self.__class__.__name__, assets_folder=str(self.Assets), external_stylesheets=external, suppress_callback_exceptions=True, title=self._title_, update_title=None, meta_tags=self._META_)
        if overlay: self._serve_(app)
        return app

    def asset(self, path: str, url: bool = True) -> str:
        if self._assets_ != self.Assets and (self._assets_ / path).exists():
            return f"{self._APPLICATION_}/{path}" if url else self._read_(self._assets_ / path)
        if (self.Assets / path).exists():
            return self.app.get_asset_url(path) if url else self._read_(self.Assets / path)
        raise RuntimeError(f"Asset Operation: Failed · Due to Missing Asset ({path})")

    def __init_ids__(self) -> None:
        self.GLOBAL_LOCATION_ID = self.register(type="location", name="location")
        self.GLOBAL_ROUTING_STORAGE_ID = self.register(type="storage", name="routing")
        self.GLOBAL_BRAND_ID = self.register(type="link", name="brand")
        self.GLOBAL_NAVIGATION_ID = self.register(type="navigator", name="navigation")
        self.GLOBAL_NAVIGATION_TOGGLE_ID = self.register(type="button", name="navigation-toggle")
        self.GLOBAL_CONTENT_ID = self.register(type="div", name="content")
        self.GLOBAL_CONTENT_LOADING_ID = self.register(type="loading", name="content")
        self.GLOBAL_SIDEBAR_ID = self.register(type="div", name="sidebar")
        self.GLOBAL_SIDEBAR_BUTTON_ID = self.register(type="button", name="sidebar")
        self.GLOBAL_SIDEBAR_LOADING_ID = self.register(type="loading", name="sidebar")
        self.GLOBAL_SIDEBAR_COLLAPSE_ID = self.register(type="collapse", name="sidebar")
        self.GLOBAL_CONTACTS_ARROW_ID = self.register(type="icon", name="contacts")
        self.GLOBAL_CONTACTS_BUTTON_ID = self.register(type="button", name="contacts")
        self.GLOBAL_CONTACTS_COLLAPSE_ID = self.register(type="collapse", name="contacts")
        self.GLOBAL_CONTACTS_ID = self.register(type="card", name="contacts")
        self.GLOBAL_IMPORT_ID = self.register(type="button", name="import")
        self.GLOBAL_IMPORT_UPLOAD_ID = self.register(type="upload", name="import")
        self.GLOBAL_EXPORT_ID = self.register(type="button", name="export")
        self.GLOBAL_EXPORT_DOWNLOAD_ID = self.register(type="download", name="export")
        self.GLOBAL_ENTER_ASYNC_ID = self.register(type="asyncer", name="enter")
        self.GLOBAL_REENTER_ASYNC_ID = self.register(type="asyncer", name="reenter")
        self.GLOBAL_ROUTE_ASYNC_ID = self.register(type="asyncer", name="route")
        self.GLOBAL_LEAVE_ASYNC_ID = self.register(type="asyncer", name="leave")
        self.GLOBAL_MEMORY_STORAGE_ID = self.register(type="storage", name="memory", portable="data")
        self.GLOBAL_SESSION_STORAGE_ID = self.register(type="storage", name="session", portable="data")
        self.GLOBAL_LOCAL_STORAGE_ID = self.register(type="storage", name="local", portable="data")
        self.GLOBAL_CLEAN_MEMORY_BUTTON_ID = self.register(type="button", name="memory")
        self.GLOBAL_CLEAN_MEMORY_ASYNC_ID = self.register(type="asyncer", name="memory")
        self.GLOBAL_CLEAN_SESSION_BUTTON_ID = self.register(type="button", name="session")
        self.GLOBAL_CLEAN_SESSION_ASYNC_ID = self.register(type="asyncer", name="session")
        self.GLOBAL_CLEAN_LOCAL_BUTTON_ID = self.register(type="button", name="local")
        self.GLOBAL_CLEAN_LOCAL_ASYNC_ID = self.register(type="asyncer", name="local")
        self.GLOBAL_CLEAN_RESET_BUTTON_ID = self.register(type="button", name="reset")
        self.GLOBAL_CLEAN_RESET_ASYNC_ID = self.register(type="asyncer", name="reset")
        self.GLOBAL_MODAL_ID = self.register(type="modal", name="global")
        self.GLOBAL_MODAL_HEADER_ID = self.register(type="div", name="modal_header")
        self.GLOBAL_MODAL_BODY_ID = self.register(type="div", name="modal_body")
        self.GLOBAL_MODAL_FOOTER_ID = self.register(type="div", name="modal_footer")
        self.GLOBAL_MODAL_BUTTON_ID = self.register(type="button", name="modal_close")
        self.GLOBAL_EMAIL_STORAGE_ID = self.register(type="storage", name="email")
        self.GLOBAL_NOTIFICATION_ID = self.register(type="div", name="notification")
        self.GLOBAL_MOTTO_ID = self.register(type="text", name="motto")
        self.GLOBAL_MOTTO_ASYNC_ID = self.register(type="storage", name="motto")
        self.GLOBAL_THEME_STORAGE_ID = self.register(type="storage", name="theme")
        self.GLOBAL_THEME_TOGGLE_ID = self.register(type="menuitem", name="theme")
        self.GLOBAL_THEME_ICON_ID = self.register(type="icon", name="theme")
        self.GLOBAL_USER_STORAGE_ID = self.register(type="storage", name="user")
        self.GLOBAL_MENU_ID = self.register(type="menu", name="account")
        self.GLOBAL_ACCOUNT_ICON_ID = self.register(type="icon", name="account")
        self.GLOBAL_MENU_USER_ID = self.register(type="text", name="user")
        self.GLOBAL_MENU_SESSION_ID = self.register(type="menuitem", name="session")
        self.GLOBAL_MENU_SETTINGS_ID = self.register(type="menuitem", name="settings")
        self.GLOBAL_LOGIN_OPEN_ID = self.register(type="menuitem", name="login")
        self.GLOBAL_LOGIN_ICON_ID = self.register(type="icon", name="login")
        self.GLOBAL_LOGIN_LABEL_ID = self.register(type="text", name="login")
        self.GLOBAL_SETTINGS_THEME_ID = self.register(type="button", name="settings_theme")
        self.GLOBAL_SETTINGS_THEME_ICON_ID = self.register(type="icon", name="settings_theme")
        self.GLOBAL_SETTINGS_THEME_LABEL_ID = self.register(type="text", name="settings_theme")
        self.GLOBAL_SETTINGS_AUTH_ID = self.register(type="button", name="settings_auth")
        self.GLOBAL_SETTINGS_AUTH_ICON_ID = self.register(type="icon", name="settings_auth")
        self.GLOBAL_SETTINGS_AUTH_LABEL_ID = self.register(type="text", name="settings_auth")
        self.GLOBAL_LOGINPAGE_USER_ID = self.register(type="input", name="loginpage_username")
        self.GLOBAL_LOGINPAGE_PASS_ID = self.register(type="input", name="loginpage_password")
        self.GLOBAL_LOGINPAGE_SUBMIT_ID = self.register(type="button", name="loginpage_submit")
        self.GLOBAL_LOGINPAGE_SIGNUP_ID = self.register(type="button", name="loginpage_signup")
        self.ids()

    def _init_ids_(self) -> None:
        self.__init_ids__()
        self._log_.debug(lambda: f"Identify Operation: Registered ({len(self._ids_)} Ids)")


    def _init_pages_(self) -> None:
        launchpad = self.Launchpad(app=self)
        self.link(launchpad)
        self.pages()
        self.link(SettingsPageAPI(app=self))
        login = LoginPageAPI(app=self)
        login.anchor = self.anchorize(path="/login", relative=True)
        login.endpoint = self.endpointize(path="/login", relative=True)
        login._init_()
        self.index(endpoint=login.endpoint, page=login)
        launchpad.refresh()
        self._log_.debug(lambda: f"Pages Operation: Loaded ({len(self._pages_)} Pages)")


    def __register_callback__(self, context, func, name: str, is_page: bool) -> None:
        is_client = getattr(func, "js", False)
        args = list(getattr(func, "args", []))
        kwargs = dict(getattr(func, "kwargs", {}))
        kwargs.pop("memoize", None)
        manager = kwargs.pop("manager", None)
        if not kwargs.pop("background", False): kwargs.pop("background", None)
        else: kwargs["background"] = True
        if manager: kwargs["background_callback_manager"] = manager
        target = getattr(context, name)() if is_client else getattr(context, name)
        running_extras, cancel_extras, specs = [], [], []
        for injection in self._injector_.match(func):
            mode = InjectionType.coerce(getattr(func, injection.flag, False), injection.default)
            if mode is InjectionType.Disabled: continue
            running_extras.extend(injection.running())
            cancel_extras.extend(injection.cancel())
            spec = injection.spec(app=self, is_page=is_page, mode=mode)
            if spec["args"] or spec["pre"] or spec["post"] or spec["pre_js"] or spec["post_js"]: specs.append(spec)
        if specs:
            target, args = inject_clientside(specs, target, args) if is_client else inject_serverside(specs, target, args)
        for attr in ("running", "cancel", "progress", "interval", "progress_default"):
            value = getattr(func, attr, None)
            if attr == "running" and running_extras: value = (value or []) + running_extras
            elif attr == "cancel" and cancel_extras: value = (value or []) + cancel_extras
            if value is None: continue
            if attr == "running":
                kwargs[attr] = [(item[0].build(context), item[1], item[2]) if isinstance(item, (list, tuple)) and len(item) == 3 and isinstance(item[0], Trigger) else item for item in value]
            elif attr in ("cancel", "progress") and isinstance(value, list):
                kwargs[attr] = [item.build(context) if isinstance(item, Trigger) else item for item in value]
            elif isinstance(value, Trigger):
                kwargs[attr] = value.build(context)
            else:
                kwargs[attr] = value
        args = [arg.build(context=context) if isinstance(arg, Trigger) else arg for arg in args]
        if is_client:
            self.app.clientside_callback(target, *args, **kwargs)
            self._log_.debug(lambda: f"Callback Operation: Registered (Clientside) · {name}")
        else:
            self.app.callback(*args, **kwargs)(target)
            self._log_.debug(lambda: f"Callback Operation: Registered (Serverside) · {name}")

    def __register_callbacks__(self) -> None:
        for context in [self] + list(self._pages_.values()):
            is_page = isinstance(context, PageAPI)
            processed = set()
            for cls in getmro(context):
                if cls is object: continue
                for name, func in cls.__dict__.items():
                    if name in processed or not iscallable(func) or not getattr(func, "callback", False): continue
                    processed.add(name)
                    self.__register_callback__(context, func, name, is_page)

    def _init_callbacks_(self) -> None:
        self.__register_callbacks__()
        self._log_.debug(lambda: f"Wire Operation: Wired ({len(self.app.callback_map)} Callbacks)")

    @clientside_callback(
        Output(GlobalAPI.GLOBAL_SIDEBAR_COLLAPSE_ID, "is_open"),
        Input(GlobalAPI.GLOBAL_SIDEBAR_BUTTON_ID, "n_clicks"),
        State(GlobalAPI.GLOBAL_SIDEBAR_COLLAPSE_ID, "is_open"),
        on_click=InjectionType.Hidden
    )
    def _global_async_sidebar_button_callback_(self):
        return self.asset("Callbacks/Collapse.js", url=False)

    @clientside_callback(
        Output(GlobalAPI.GLOBAL_CONTACTS_COLLAPSE_ID, "is_open"),
        Output(GlobalAPI.GLOBAL_CONTACTS_ARROW_ID, "className"),
        Input(GlobalAPI.GLOBAL_CONTACTS_BUTTON_ID, "n_clicks"),
        State(GlobalAPI.GLOBAL_CONTACTS_COLLAPSE_ID, "is_open"),
        State(GlobalAPI.GLOBAL_CONTACTS_ARROW_ID, "className"),
        on_click=InjectionType.Hidden
    )
    def _global_async_contacts_button_callback_(self):
        return self.asset("Callbacks/Collapse.js", url=False)

    @clientside_callback(
        Output(GlobalAPI.GLOBAL_EMAIL_STORAGE_ID, "data"),
        Input(GlobalAPI.GLOBAL_EMAIL_STORAGE_ID, "data")
    )
    def _global_async_email_client_callback_(self):
        return self.asset("Callbacks/Email.js", url=False)

    @serverside_callback(
        Output(GlobalAPI.GLOBAL_MOTTO_ID, "children"),
        Input(GlobalAPI.GLOBAL_MOTTO_ASYNC_ID, "data"),
        on_init=InjectionType.Hidden
    )
    def _global_async_motto_callback_(self, trigger):
        if not self._mottos_: return dash.no_update
        return random.choice(self._mottos_)

    @clientside_callback(
        Output(GlobalAPI.GLOBAL_IMPORT_UPLOAD_ID, "contents"),
        Input(GlobalAPI.GLOBAL_IMPORT_UPLOAD_ID, "contents"),
        State(GlobalAPI.GLOBAL_IMPORT_UPLOAD_ID, "filename")
    )
    def _global_async_import_snapshot_callback_(self):
        return self.asset("Callbacks/Import.js", url=False)

    _PORTABLES_ = ("data", "value", "input", "filter", "date", "checked", "start_date", "end_date", "options", "disabled", "is_open", "active_tab")

    @clientside_callback(
        Output(GlobalAPI.GLOBAL_EXPORT_DOWNLOAD_ID, "data"),
        Input(GlobalAPI.GLOBAL_EXPORT_ID, "n_clicks"),
        State(GlobalAPI.GLOBAL_LOCATION_ID, "pathname"),
        *[State({"app": dash.ALL, "page": dash.ALL, "type": dash.ALL, "name": dash.ALL, "portable": portable}, portable) for portable in _PORTABLES_]
    )
    def _global_async_export_snapshot_callback_(self):
        return self.asset("Callbacks/Export.js", url=False)

    @clientside_callback(
        Output(GlobalAPI.GLOBAL_MEMORY_STORAGE_ID, "data"),
        on_clean_memory=InjectionType.Hidden
    )
    def _global_async_clean_memory_callback_(self):
        return self.asset("Callbacks/Clear.js", url=False)

    @clientside_callback(
        Output(GlobalAPI.GLOBAL_SESSION_STORAGE_ID, "data"),
        on_clean_session=InjectionType.Hidden
    )
    def _global_async_clean_session_callback_(self):
        return self.asset("Callbacks/Clear.js", url=False)

    @clientside_callback(
        Output(GlobalAPI.GLOBAL_LOCAL_STORAGE_ID, "data"),
        on_clean_local=InjectionType.Hidden
    )
    def _global_async_clean_local_callback_(self):
        return self.asset("Callbacks/Clear.js", url=False)

    @clientside_callback(
        Output(GlobalAPI.GLOBAL_CLEAN_MEMORY_ASYNC_ID, "data"),
        Output(GlobalAPI.GLOBAL_CLEAN_SESSION_ASYNC_ID, "data"),
        Output(GlobalAPI.GLOBAL_CLEAN_LOCAL_ASYNC_ID, "data"),
        State(GlobalAPI.GLOBAL_CLEAN_MEMORY_ASYNC_ID, "data"),
        State(GlobalAPI.GLOBAL_CLEAN_SESSION_ASYNC_ID, "data"),
        State(GlobalAPI.GLOBAL_CLEAN_LOCAL_ASYNC_ID, "data"),
        on_clean_reset=InjectionType.Hidden
    )
    def _global_async_clean_reset_callback_(self):
        return self.asset("Callbacks/Reset.js", url=False)

    @clientside_callback(
        Output(GlobalAPI.GLOBAL_MODAL_ID, "is_open"),
        Input(GlobalAPI.GLOBAL_MODAL_BUTTON_ID, "n_clicks")
    )
    def _global_async_dismiss_modal_callback_(self):
        return self.asset("Callbacks/Dismiss.js", url=False)

    @clientside_callback(
        Output(GlobalAPI.GLOBAL_THEME_STORAGE_ID, "data"),
        Input(GlobalAPI.GLOBAL_THEME_TOGGLE_ID, "n_clicks"),
        State(GlobalAPI.GLOBAL_THEME_STORAGE_ID, "data"),
        on_click=InjectionType.Hidden
    )
    def _global_async_theme_toggle_callback_(self):
        return self.asset("Callbacks/Theme.js", url=False)

    @clientside_callback(
        Output(GlobalAPI.GLOBAL_THEME_STORAGE_ID, "data"),
        Input(GlobalAPI.GLOBAL_SETTINGS_THEME_ID, "n_clicks"),
        State(GlobalAPI.GLOBAL_THEME_STORAGE_ID, "data"),
        on_click=InjectionType.Hidden
    )
    def _global_async_settings_theme_callback_(self):
        return self.asset("Callbacks/Theme.js", url=False)

    @clientside_callback(
        Output(GlobalAPI.GLOBAL_SETTINGS_THEME_ICON_ID, "className"),
        Output(GlobalAPI.GLOBAL_SETTINGS_THEME_LABEL_ID, "children"),
        Input(GlobalAPI.GLOBAL_THEME_STORAGE_ID, "data"),
        on_init=InjectionType.Hidden
    )
    def _global_async_settings_theme_display_callback_(self):
        return self.asset("Callbacks/ThemeDisplay.js", url=False)

    @clientside_callback(
        Output(GlobalAPI.GLOBAL_SETTINGS_AUTH_ICON_ID, "className"),
        Output(GlobalAPI.GLOBAL_SETTINGS_AUTH_LABEL_ID, "children"),
        Input(GlobalAPI.GLOBAL_USER_STORAGE_ID, "data"),
        on_init=InjectionType.Hidden
    )
    def _global_async_settings_auth_display_callback_(self):
        return self.asset("Callbacks/AuthDisplay.js", url=False)

    @clientside_callback(
        Output(GlobalAPI.GLOBAL_THEME_ICON_ID, "className"),
        Input(GlobalAPI.GLOBAL_THEME_STORAGE_ID, "data"),
        on_init=InjectionType.Hidden
    )
    def _global_async_theme_apply_callback_(self):
        return self.asset("Callbacks/ThemeApply.js", url=False)

    @clientside_callback(
        Output(GlobalAPI.GLOBAL_ACCOUNT_ICON_ID, "className"),
        Output(GlobalAPI.GLOBAL_MENU_USER_ID, "children"),
        Output(GlobalAPI.GLOBAL_LOGIN_ICON_ID, "className"),
        Output(GlobalAPI.GLOBAL_LOGIN_LABEL_ID, "children"),
        Input(GlobalAPI.GLOBAL_USER_STORAGE_ID, "data"),
        on_init=InjectionType.Hidden
    )
    def _global_async_menu_user_callback_(self):
        return self.asset("Callbacks/Account.js", url=False)

    @serverside_callback(
        Output(GlobalAPI.GLOBAL_LOCATION_ID, "pathname"),
        Input(GlobalAPI.GLOBAL_LOGIN_OPEN_ID, "n_clicks"),
        Input(GlobalAPI.GLOBAL_SETTINGS_AUTH_ID, "n_clicks"),
        State(GlobalAPI.GLOBAL_USER_STORAGE_ID, "data")
    )
    def _global_async_session_callback_(self, menu_clicks, settings_clicks, user):
        trigger = dash.ctx.triggered_id
        clicked = (trigger == self.GLOBAL_LOGIN_OPEN_ID and menu_clicks) or (trigger == self.GLOBAL_SETTINGS_AUTH_ID and settings_clicks)
        if not clicked: return dash.no_update
        if user:
            if self._auth_ is not None: self._auth_.logout()
            self._log_.info(lambda: f"Authenticate Operation: Revoked ({user.get('name') if isinstance(user, dict) else user})")
            self.notify.info("Signed out", header="Session Ended")
        return self._login_

    @serverside_callback(
        Output(GlobalAPI.GLOBAL_LOCATION_ID, "pathname"),
        Input(GlobalAPI.GLOBAL_LOGINPAGE_SUBMIT_ID, "n_clicks"),
        Input(GlobalAPI.GLOBAL_LOGINPAGE_PASS_ID, "n_submit"),
        State(GlobalAPI.GLOBAL_LOGINPAGE_USER_ID, "value"),
        State(GlobalAPI.GLOBAL_LOGINPAGE_PASS_ID, "value")
    )
    def _global_async_login_page_callback_(self, submit_clicks, submit_enter, username, password):
        if not submit_clicks and not submit_enter:
            return dash.no_update
        if (result := self.authenticate(username, password)):
            self._log_.info(lambda: f"Authenticate Operation: Granted ({result})")
            self.notify.success(f"Signed in as {result}", header="Authenticated")
            return self._endpoint_
        self._log_.warning(lambda: "Authenticate Operation: Failed · Due to Invalid Credentials")
        self.notify.error("Invalid credentials", header="Authentication Failed")
        return dash.no_update

    @serverside_callback(
        Output(GlobalAPI.GLOBAL_EMAIL_STORAGE_ID, "data"),
        Input(GlobalAPI.GLOBAL_LOGINPAGE_SIGNUP_ID, "n_clicks"),
        State(GlobalAPI.GLOBAL_LOGINPAGE_USER_ID, "value")
    )
    def _global_async_signup_request_callback_(self, signup_clicks, requester):
        if not signup_clicks:
            return dash.no_update
        if not self._contact_:
            self.notify.warning("Access requests are not available", header="Request Access")
            return dash.no_update
        message = "\n".join([f"I would like to request access to {self._name_}.", "", f"Email: {requester or ''}", "Name: ", "Team: ", "Reason: "])
        self._log_.info(lambda: f"Signup Operation: Requested ({requester or 'Unknown'})")
        self.notify.info("Your email client will open — send the request to the team to complete it", header="Request Access")
        return {"to": self._contact_, "subject": f"Access Request · {self._name_}", "message": message}

    def ids(self) -> None:
        pass

    def components(self) -> None:
        pass

    def pages(self) -> None:
        pass

    def apps(self) -> list[LinkAPI]:
        return []

    def _required_(self, page: PageAPI | None):
        from Library.Auth import RoleAPI
        app_access = RoleAPI.parse(self._access_) if self._access_ is not None else RoleAPI.Public
        page_access = RoleAPI.parse(getattr(page, "access", None)) if page is not None else RoleAPI.Public
        app_access = app_access if isinstance(app_access, RoleAPI) else RoleAPI.Public
        page_access = page_access if isinstance(page_access, RoleAPI) else RoleAPI.Public
        return app_access if app_access.value >= page_access.value else page_access

    def _private_(self) -> bool:
        from Library.Auth import RoleAPI
        access = RoleAPI.parse(self._access_) if self._access_ is not None else RoleAPI.Public
        return isinstance(access, RoleAPI) and access.value > RoleAPI.Public.value

    def authenticate(self, username: str | None, password: str | None) -> str | None:
        if self._auth_ is None: return username or None
        identity = self._auth_.login(username=username, password=password)
        return identity.get_id() if identity else None

    def run(self) -> None:
        self._log_.info(lambda: f"Run Operation: Serving (http://{self._host_}:{self._port_})")
        self.app.run(host=self._host_, port=self._port_, debug=self._debug_, use_reloader=False, dev_tools_silence_routes_logging=False)

    def mount(self, path: str = "/") -> FastAPI:
        server = FastAPI(title=self._title_)
        server.mount(path, WSGIMiddleware(self.app.server))
        self._log_.info(lambda: f"Mount Operation: Mounted ({path})")
        return server

    def __repr__(self) -> str:
        return repr(f"{self.__class__.__name__} @ http://{self._host_}:{self._port_}")