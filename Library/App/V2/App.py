from __future__ import annotations

import inspect
from pathlib import Path, PurePosixPath

import dash
import flask
from dash import dcc, html
import dash_bootstrap_components as dbc
from fastapi import FastAPI
from fastapi.middleware.wsgi import WSGIMiddleware

from Library.App.V2.Callback import ComponentID, Output, Input, State, Trigger, InjectionType, serverside_callback, clientside_callback, inject_serverside, inject_clientside
from Library.App.V2.Component import Component, ButtonAPI, IconAPI, LoadingAPI, ModalAPI, StorageAPI, TextAPI
from Library.App.V2.Injection import InjectorAPI
from Library.App.V2.Layout import DefaultLayoutAPI
from Library.App.V2.Notification import NotifierAPI
from Library.App.V2.Page import PageAPI
from Library.App.V2.Session import TriggerAPI
from Library.App.V2.Launchpad import LaunchpadPageAPI
from Library.App.V2.Settings import SettingsPageAPI
from Library.Logging import HandlerLoggingAPI
from Library.Utility.Path import inspect_file, inspect_file_path
from Library.Utility.Runtime import find_host_port
from Library.Utility.Typing import MISSING, getmro, iscallable

class AppAPI:

    THEME = [dbc.themes.BOOTSTRAP, dbc.icons.BOOTSTRAP]
    Assets = Path(__file__).parent / "Assets"
    _FRAMEWORK_ = "/_framework"

    GLOBAL_LOCATION_ID: ComponentID | dict = ComponentID()
    GLOBAL_ROUTING_STORAGE_ID: ComponentID | dict = ComponentID()
    GLOBAL_BRAND_ID: ComponentID | dict = ComponentID()
    GLOBAL_NAVIGATION_ID: ComponentID | dict = ComponentID()
    GLOBAL_CONTENT_ID: ComponentID | dict = ComponentID()
    GLOBAL_CONTENT_LOADING_ID: ComponentID | dict = ComponentID()
    GLOBAL_SIDEBAR_ID: ComponentID | dict = ComponentID()
    GLOBAL_SIDEBAR_BUTTON_ID: ComponentID | dict = ComponentID()
    GLOBAL_SIDEBAR_LOADING_ID: ComponentID | dict = ComponentID()
    GLOBAL_SIDEBAR_COLLAPSE_ID: ComponentID | dict = ComponentID()

    GLOBAL_CONTACTS_ARROW_ID: ComponentID | dict = ComponentID()
    GLOBAL_CONTACTS_BUTTON_ID: ComponentID | dict = ComponentID()
    GLOBAL_CONTACTS_COLLAPSE_ID: ComponentID | dict = ComponentID()
    GLOBAL_CONTACTS_ID: ComponentID | dict = ComponentID()

    GLOBAL_IMPORT_ID: ComponentID | dict = ComponentID()
    GLOBAL_IMPORT_UPLOAD_ID: ComponentID | dict = ComponentID()
    GLOBAL_EXPORT_ID: ComponentID | dict = ComponentID()
    GLOBAL_EXPORT_DOWNLOAD_ID: ComponentID | dict = ComponentID()

    GLOBAL_ENTER_ASYNC_ID: ComponentID | dict = ComponentID()
    GLOBAL_REENTER_ASYNC_ID: ComponentID | dict = ComponentID()
    GLOBAL_ROUTE_ASYNC_ID: ComponentID | dict = ComponentID()
    GLOBAL_LEAVE_ASYNC_ID: ComponentID | dict = ComponentID()

    GLOBAL_MEMORY_STORAGE_ID: ComponentID | dict = ComponentID()
    GLOBAL_SESSION_STORAGE_ID: ComponentID | dict = ComponentID()
    GLOBAL_LOCAL_STORAGE_ID: ComponentID | dict = ComponentID()

    GLOBAL_CLEAN_MEMORY_BUTTON_ID: ComponentID | dict = ComponentID()
    GLOBAL_CLEAN_MEMORY_ASYNC_ID: ComponentID | dict = ComponentID()
    GLOBAL_CLEAN_SESSION_BUTTON_ID: ComponentID | dict = ComponentID()
    GLOBAL_CLEAN_SESSION_ASYNC_ID: ComponentID | dict = ComponentID()
    GLOBAL_CLEAN_LOCAL_BUTTON_ID: ComponentID | dict = ComponentID()
    GLOBAL_CLEAN_LOCAL_ASYNC_ID: ComponentID | dict = ComponentID()
    GLOBAL_CLEAN_RESET_BUTTON_ID: ComponentID | dict = ComponentID()
    GLOBAL_CLEAN_RESET_ASYNC_ID: ComponentID | dict = ComponentID()

    GLOBAL_MODAL_ID: ComponentID | dict = ComponentID()
    GLOBAL_MODAL_HEADER_ID: ComponentID | dict = ComponentID()
    GLOBAL_MODAL_BODY_ID: ComponentID | dict = ComponentID()
    GLOBAL_MODAL_FOOTER_ID: ComponentID | dict = ComponentID()
    GLOBAL_MODAL_BUTTON_ID: ComponentID | dict = ComponentID()

    GLOBAL_EMAIL_STORAGE_ID: ComponentID | dict = ComponentID()
    GLOBAL_NOTIFICATION_ID: ComponentID | dict = ComponentID()

    GLOBAL_THEME_STORAGE_ID: ComponentID | dict = ComponentID()
    GLOBAL_THEME_TOGGLE_ID: ComponentID | dict = ComponentID()
    GLOBAL_THEME_ICON_ID: ComponentID | dict = ComponentID()
    GLOBAL_USER_STORAGE_ID: ComponentID | dict = ComponentID()
    GLOBAL_MENU_LOCK_ID: ComponentID | dict = ComponentID()
    GLOBAL_MENU_USER_ID: ComponentID | dict = ComponentID()
    GLOBAL_LOGIN_OPEN_ID: ComponentID | dict = ComponentID()
    GLOBAL_LOGIN_ICON_ID: ComponentID | dict = ComponentID()
    GLOBAL_LOGIN_LABEL_ID: ComponentID | dict = ComponentID()
    GLOBAL_LOGIN_MODAL_ID: ComponentID | dict = ComponentID()
    GLOBAL_LOGIN_USER_ID: ComponentID | dict = ComponentID()
    GLOBAL_LOGIN_PASS_ID: ComponentID | dict = ComponentID()
    GLOBAL_LOGIN_SUBMIT_ID: ComponentID | dict = ComponentID()

    GLOBAL_SETTINGS_THEME_ID: ComponentID | dict = ComponentID()
    GLOBAL_SETTINGS_THEME_ICON_ID: ComponentID | dict = ComponentID()
    GLOBAL_SETTINGS_THEME_LABEL_ID: ComponentID | dict = ComponentID()
    GLOBAL_SETTINGS_AUTH_ID: ComponentID | dict = ComponentID()
    GLOBAL_SETTINGS_AUTH_ICON_ID: ComponentID | dict = ComponentID()
    GLOBAL_SETTINGS_AUTH_LABEL_ID: ComponentID | dict = ComponentID()

    GLOBAL_NOT_FOUND_LAYOUT: Component
    GLOBAL_LOADING_LAYOUT: Component
    GLOBAL_MAINTENANCE_LAYOUT: Component
    GLOBAL_DEVELOPMENT_LAYOUT: Component

    def __init__(self, *,
                 name: str = "Quant",
                 title: str = MISSING,
                 team: str = MISSING,
                 contact: str = MISSING,
                 motto: str = MISSING,
                 host: str = "127.0.0.1",
                 port: int = MISSING,
                 anchor: str = "/",
                 debug: bool = False) -> None:
        self._log_ = HandlerLoggingAPI(Class=self.__class__.__name__, Subclass="App Management")
        self._name_ = name
        self._title_ = title if title is not MISSING else name
        self._team_ = team if team is not MISSING else None
        self._contact_ = contact if contact is not MISSING else None
        self._motto_ = motto if motto is not MISSING else None
        self._host_ = host
        self._port_ = port if port is not MISSING else find_host_port(host=host, port_min=8050)
        self._debug_ = debug
        self._anchor_ = inspect_file(anchor, header=True, builder=PurePosixPath)
        self._endpoint_ = inspect_file_path(anchor, header=True, footer=True, builder=PurePosixPath)
        self._ids_ = set()
        self._pages_ = {}
        self._assets_ = Path(inspect.getfile(type(self))).parent / "Assets"
        self.app = self._compose_()
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
        return {"app": self.__class__.__name__, "page": page, "type": type, "name": name, "portable": portable, **kwargs}

    def register(self, *, page: str = "global", type: str, name: str, portable: str = "", **kwargs) -> dict:
        cid = self.identify(page=page, type=type, name=name, portable=portable, **kwargs)
        key = (cid["app"], cid["page"], cid["type"], cid["name"], cid["portable"])
        if key in self._ids_: raise RuntimeError(f"Register Operation: Failed · Due to Duplicate Id ({cid})")
        self._ids_.add(key)
        return cid

    def resolve(self, *, path: PurePosixPath | str, relative: bool, footer: bool = None) -> str:
        path = inspect_file(path, header=False, builder=PurePosixPath)
        path = self._anchor_ / path if relative else path
        return inspect_file_path(path, header=True, footer=footer, builder=PurePosixPath)

    def anchorize(self, *, path: PurePosixPath | str, relative: bool = True) -> str:
        return self.resolve(path=path, relative=relative, footer=False)

    def endpointize(self, *, path: PurePosixPath | str, relative: bool = True) -> str:
        return self.resolve(path=path, relative=relative, footer=True)

    def locate(self, *, endpoint: str) -> tuple[str, PageAPI | None]:
        return endpoint, self._pages_.get(endpoint, None)

    def redirect(self, *, endpoint: str) -> tuple[str, PageAPI | None]:
        endpoint, page = self.locate(endpoint=endpoint)
        while page and page.endpoint != page.redirect:
            endpoint, page = self.locate(endpoint=page.redirect)
        return endpoint, page

    def index(self, *, endpoint: str, page: PageAPI) -> None:
        self._pages_[endpoint] = page
        self._log_.debug(lambda: f"Index Operation: Indexed ({endpoint})")

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
        assets = self.Assets
        def _view_(filename): return flask.send_from_directory(assets, filename)
        app.server.add_url_rule(f"{self._FRAMEWORK_}/<path:filename>", endpoint=f"framework_{id(self)}", view_func=_view_)

    def _compose_(self) -> dash.Dash:
        override = self._assets_.exists() and self._assets_ != self.Assets
        external = list(self.THEME)
        if override: external += [f"{self._FRAMEWORK_}/{css.relative_to(self.Assets).as_posix()}" for css in sorted(self.Assets.rglob("*.css"))]
        else: self._assets_ = self.Assets
        app = dash.Dash(self.__class__.__name__, assets_folder=str(self._assets_), external_stylesheets=external, suppress_callback_exceptions=True, title=self._title_, update_title=None)
        if override: self._serve_(app)
        return app

    def asset(self, path: str, url: bool = True) -> str:
        if self._assets_ != self.Assets and (self._assets_ / path).exists():
            return self.app.get_asset_url(path) if url else self._read_(self._assets_ / path)
        if (self.Assets / path).exists():
            if not url: return self._read_(self.Assets / path)
            return f"{self._FRAMEWORK_}/{path}" if self._assets_ != self.Assets else self.app.get_asset_url(path)
        raise RuntimeError(f"Asset Operation: Failed · Due to Missing Asset ({path})")

    def __init_ids__(self) -> None:
        self.GLOBAL_LOCATION_ID = self.register(type="location", name="location")
        self.GLOBAL_ROUTING_STORAGE_ID = self.register(type="storage", name="routing")
        self.GLOBAL_BRAND_ID = self.register(type="link", name="brand")
        self.GLOBAL_NAVIGATION_ID = self.register(type="navigator", name="navigation")
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
        self.GLOBAL_THEME_STORAGE_ID = self.register(type="storage", name="theme")
        self.GLOBAL_THEME_TOGGLE_ID = self.register(type="menuitem", name="theme")
        self.GLOBAL_THEME_ICON_ID = self.register(type="icon", name="theme")
        self.GLOBAL_USER_STORAGE_ID = self.register(type="storage", name="user")
        self.GLOBAL_MENU_LOCK_ID = self.register(type="icon", name="lock")
        self.GLOBAL_MENU_USER_ID = self.register(type="text", name="user")
        self.GLOBAL_LOGIN_OPEN_ID = self.register(type="menuitem", name="login")
        self.GLOBAL_LOGIN_ICON_ID = self.register(type="icon", name="login")
        self.GLOBAL_LOGIN_LABEL_ID = self.register(type="text", name="login")
        self.GLOBAL_LOGIN_MODAL_ID = self.register(type="modal", name="login")
        self.GLOBAL_LOGIN_USER_ID = self.register(type="input", name="username")
        self.GLOBAL_LOGIN_PASS_ID = self.register(type="input", name="password")
        self.GLOBAL_LOGIN_SUBMIT_ID = self.register(type="button", name="login")
        self.GLOBAL_SETTINGS_THEME_ID = self.register(type="button", name="settings_theme")
        self.GLOBAL_SETTINGS_THEME_ICON_ID = self.register(type="icon", name="settings_theme")
        self.GLOBAL_SETTINGS_THEME_LABEL_ID = self.register(type="text", name="settings_theme")
        self.GLOBAL_SETTINGS_AUTH_ID = self.register(type="button", name="settings_auth")
        self.GLOBAL_SETTINGS_AUTH_ICON_ID = self.register(type="icon", name="settings_auth")
        self.GLOBAL_SETTINGS_AUTH_LABEL_ID = self.register(type="text", name="settings_auth")
        self.ids()

    def _init_ids_(self) -> None:
        self.__init_ids__()
        self._log_.debug(lambda: f"Identify Operation: Registered ({len(self._ids_)} Ids)")

    def __init_default_layout__(self) -> None:
        self.GLOBAL_NOT_FOUND_LAYOUT = DefaultLayoutAPI(icon="bi bi-compass", title="Resource Not Found", description="Unable to find the resource you are looking for", details="Please check the URL path", classname="empty").build()
        self.GLOBAL_LOADING_LAYOUT = DefaultLayoutAPI(icon="bi bi-hourglass-split", title="Loading", description="This resource is loading its content", details="Please wait a moment", classname="loading").build()
        self.GLOBAL_MAINTENANCE_LAYOUT = DefaultLayoutAPI(icon="bi bi-tools", title="Under Maintenance", description="This resource is temporarily down for maintenance", details="Please try again later", classname="maintenance").build()
        self.GLOBAL_DEVELOPMENT_LAYOUT = DefaultLayoutAPI(icon="bi bi-cone-striped", title="Under Development", description="This resource is currently under development", details="Please try again later", classname="development").build()

    def __init_header_layout__(self) -> Component:
        titles = [html.Span(self._name_, className="app-brand-name")]
        if self._team_: titles.append(html.Span(self._team_, className="app-brand-team"))
        brand = dcc.Link([html.Img(src=self.asset("Images/logo.png"), className="app-logo"), html.Div(titles, className="app-brand-titles")], href=self._endpoint_, id=self.GLOBAL_BRAND_ID, className="app-brand")
        nav = html.Div(id=self.GLOBAL_NAVIGATION_ID, className="app-nav")
        return html.Header([brand, self._tip_(self.GLOBAL_BRAND_ID, "Go to Launchpad page"), nav, self.__init_menu_layout__()], className="app-header")

    def __init_menu_layout__(self) -> Component:
        settings = self.endpointize(path="/settings", relative=True)
        label = html.Span([html.I(className="bi bi-unlock app-lock app-lock-guest", id=self.GLOBAL_MENU_LOCK_ID), html.Span("Guest", id=self.GLOBAL_MENU_USER_ID)], className="app-menu-label")
        items = [
            dbc.DropdownMenuItem([html.I(className="bi bi-box-arrow-in-right", id=self.GLOBAL_LOGIN_ICON_ID), html.Span("Sign In", id=self.GLOBAL_LOGIN_LABEL_ID)], id=self.GLOBAL_LOGIN_OPEN_ID, n_clicks=0, className="app-menu-item"),
            dbc.DropdownMenuItem([html.I(className="bi bi-moon-stars", id=self.GLOBAL_THEME_ICON_ID), html.Span("Theme")], id=self.GLOBAL_THEME_TOGGLE_ID, n_clicks=0, className="app-menu-item"),
            dbc.DropdownMenuItem(divider=True),
            dbc.DropdownMenuItem([html.I(className="bi bi-clock-history"), html.Span("Session")], href=f"{settings}#session", className="app-menu-item"),
            dbc.DropdownMenuItem([html.I(className="bi bi-gear"), html.Span("Settings")], href=settings, className="app-menu-item"),
        ]
        return dbc.DropdownMenu(items, label=label, align_end=True, nav=True, in_navbar=True, className="app-menu")

    def __init_body_layout__(self) -> Component:
        sidebar = html.Div([
            dbc.Collapse(html.Div([
                html.Div(self.GLOBAL_LOADING_LAYOUT, id=self.GLOBAL_SIDEBAR_ID, className="page"),
                *LoadingAPI(id=self.GLOBAL_SIDEBAR_LOADING_ID, hidden=True).build()
            ], className="sidebar"), id=self.GLOBAL_SIDEBAR_COLLAPSE_ID, is_open=False, dimension="width", className="sidebar-collapse"),
        ], className="aside")
        content = html.Div([
            html.Div(self.GLOBAL_LOADING_LAYOUT, id=self.GLOBAL_CONTENT_ID, className="page"),
            *LoadingAPI(id=self.GLOBAL_CONTENT_LOADING_ID, hidden=True).build()
        ], className="content")
        return html.Main([sidebar, content], className="app-body")

    def __init_footer_layout__(self) -> Component:
        left = html.Div([
            *ButtonAPI(id=self.GLOBAL_SIDEBAR_BUTTON_ID, background="primary", label=[IconAPI(icon="bi bi-layout-sidebar-inset")]).build(),
            *ButtonAPI(id=self.GLOBAL_CONTACTS_BUTTON_ID, background="primary", label=[IconAPI(icon="bi bi-caret-down-fill", id=self.GLOBAL_CONTACTS_ARROW_ID), TextAPI(text=" Contacts "), IconAPI(icon="bi bi-question-circle")]).build(),
            *ButtonAPI(id=self.GLOBAL_IMPORT_ID, upload=self.GLOBAL_IMPORT_UPLOAD_ID, background="warning", label=[TextAPI(text="Import "), IconAPI(icon="bi bi-upload")]).build(),
            *ButtonAPI(id=self.GLOBAL_EXPORT_ID, download=self.GLOBAL_EXPORT_DOWNLOAD_ID, background="warning", label=[TextAPI(text="Export "), IconAPI(icon="bi bi-download")]).build(),
            dbc.Collapse(dbc.Card(dbc.CardBody([
                html.Div([html.B("Team: "), html.Span(self._team_ or "")]),
                html.Div([html.B("Contact: "), html.A(self._contact_ or "", href=f"mailto:{self._contact_}")]),
            ]), className="panel"), id=self.GLOBAL_CONTACTS_COLLAPSE_ID, is_open=False),
        ], className="left")
        center = html.Div(html.Span(self._motto_, className="app-motto") if self._motto_ else None, className="center")
        right = html.Div([
            *ButtonAPI(id=self.GLOBAL_CLEAN_RESET_BUTTON_ID, background="danger", label=[IconAPI(icon="bi bi-trash"), TextAPI(text=" Reset ")]).build(),
        ], className="right")
        return html.Footer([left, center, right], className="app-footer")

    def __init_notification_layout__(self) -> Component:
        return html.Div(id=self.GLOBAL_NOTIFICATION_ID, className="app-notifications")

    def __init_hidden_layout__(self) -> Component:
        hidden = [dcc.Location(id=self.GLOBAL_LOCATION_ID, refresh=False)]
        hidden.extend(StorageAPI(id=self.GLOBAL_ROUTING_STORAGE_ID, persistence="session").build())
        hidden.extend(StorageAPI(id=self.GLOBAL_ENTER_ASYNC_ID, persistence="memory").build())
        hidden.extend(StorageAPI(id=self.GLOBAL_REENTER_ASYNC_ID, persistence="memory").build())
        hidden.extend(StorageAPI(id=self.GLOBAL_ROUTE_ASYNC_ID, persistence="memory").build())
        hidden.extend(StorageAPI(id=self.GLOBAL_LEAVE_ASYNC_ID, persistence="memory").build())
        hidden.extend(StorageAPI(id=self.GLOBAL_CLEAN_MEMORY_ASYNC_ID, data=TriggerAPI().dict(), persistence="memory").build())
        hidden.extend(StorageAPI(id=self.GLOBAL_CLEAN_SESSION_ASYNC_ID, data=TriggerAPI().dict(), persistence="memory").build())
        hidden.extend(StorageAPI(id=self.GLOBAL_CLEAN_LOCAL_ASYNC_ID, data=TriggerAPI().dict(), persistence="memory").build())
        hidden.extend(StorageAPI(id=self.GLOBAL_CLEAN_RESET_ASYNC_ID, data=TriggerAPI().dict(), persistence="memory").build())
        hidden.extend(StorageAPI(id=self.GLOBAL_MEMORY_STORAGE_ID, persistence="memory").build())
        hidden.extend(StorageAPI(id=self.GLOBAL_SESSION_STORAGE_ID, persistence="session").build())
        hidden.extend(StorageAPI(id=self.GLOBAL_LOCAL_STORAGE_ID, persistence="local").build())
        hidden.extend(StorageAPI(id=self.GLOBAL_EMAIL_STORAGE_ID, persistence="memory").build())
        hidden.extend(StorageAPI(id=self.GLOBAL_THEME_STORAGE_ID, persistence="local").build())
        hidden.extend(StorageAPI(id=self.GLOBAL_USER_STORAGE_ID, persistence="session").build())
        return html.Div(hidden, className="app-hidden")

    def __init_modal_layout__(self) -> Component:
        modal = ModalAPI(id=self.GLOBAL_MODAL_ID, size="lg", open=False, fade=False, centered=True, keyboard=True, backdrop=True, header=[html.Div(id=self.GLOBAL_MODAL_HEADER_ID)], body=[html.Div(id=self.GLOBAL_MODAL_BODY_ID)], footer=[html.Div(id=self.GLOBAL_MODAL_FOOTER_ID, style={"flex": "1"}), *ButtonAPI(id=self.GLOBAL_MODAL_BUTTON_ID, background="primary", label=[TextAPI(text="Close")]).build()]).build()
        form = html.Form([
            dbc.Input(id=self.GLOBAL_LOGIN_USER_ID, placeholder="Username", type="text", name="username", autoComplete="username", className="app-login-input"),
            dbc.Input(id=self.GLOBAL_LOGIN_PASS_ID, placeholder="Password", type="password", name="password", autoComplete="current-password", className="app-login-input"),
        ], className="app-login-form")
        login = dbc.Modal([dbc.ModalHeader(dbc.ModalTitle([html.I(className="bi bi-key"), html.Span(f"Sign in to {self._name_}")])), dbc.ModalBody(form), dbc.ModalFooter(dbc.Button([html.I(className="bi bi-box-arrow-in-right"), html.Span("Sign In")], id=self.GLOBAL_LOGIN_SUBMIT_ID, color="primary", n_clicks=0, type="button"))], id=self.GLOBAL_LOGIN_MODAL_ID, is_open=False, centered=True)
        return html.Div([*modal, login], className="app-modal")

    def _init_layout_(self) -> None:
        self.components()
        self.__init_default_layout__()
        header = self.__init_header_layout__()
        body = self.__init_body_layout__()
        footer = self.__init_footer_layout__()
        notification = self.__init_notification_layout__()
        hidden = self.__init_hidden_layout__()
        modal = self.__init_modal_layout__()
        self.app.layout = html.Div([header, body, footer, notification, hidden, modal], className="app-shell")
        self._log_.debug(lambda: "Layout Operation: Composed (Shell)")

    def _init_pages_(self) -> None:
        launchpad = LaunchpadPageAPI(app=self)
        self.link(launchpad)
        self.pages()
        self.link(SettingsPageAPI(app=self))
        launchpad.refresh()
        self._log_.debug(lambda: f"Pages Operation: Loaded ({len(self._pages_)} Pages)")

    @staticmethod
    def _label_(page) -> list | str:
        if not page.icon: return page.button
        return [html.I(className=page.icon), html.Span(page.button)]

    @staticmethod
    def _tip_(target: dict, text: str) -> Component:
        return dbc.Tooltip(text, target=target, delay={"show": 500, "hide": 100}, placement="bottom")

    def _init_navigation_(self) -> None:
        for endpoint, page in self._pages_.items():
            if page._navigation_: continue
            if not page.parent and not page.children:
                page._navigation_ = []
                continue
            if page.parent and not page.children:
                page._navigation_ = page.parent._navigation_
                continue
            links = []
            for backward in page.backwards():
                links.append(dbc.NavLink([html.I(className="bi bi-chevron-left"), html.Span(backward.button)], href=backward.endpoint, className="app-navlink app-navlink-back"))
            for current in page.currents():
                forwards = page.forwards(current)
                if forwards and current.endpoint != page.endpoint:
                    items = [dbc.DropdownMenuItem(self._label_(forward), href=forward.endpoint) for forward in forwards]
                    links.append(dbc.DropdownMenu(items, label=self._label_(current), nav=True, in_navbar=True, toggle_style={"padding": "0"}, className="app-navlink app-navlink-drop"))
                else:
                    identifier = self.identify(type="navlink", name=current.endpoint)
                    links.append(dbc.NavLink(self._label_(current), href=current.endpoint, active="exact", id=identifier, className="app-navlink"))
                    links.append(self._tip_(identifier, f"Go to {current.button} page"))
            page._navigation_ = dbc.Nav(links, navbar=True, className="app-nav-inner")
        self._log_.debug(lambda: "Navigation Operation: Composed (Family)")

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

    @serverside_callback(
        Output(GLOBAL_LOCATION_ID, "pathname"),
        Output(GLOBAL_ROUTING_STORAGE_ID, "data"),
        Output(GLOBAL_NAVIGATION_ID, "children"),
        Output(GLOBAL_SIDEBAR_ID, "children"),
        Output(GLOBAL_CONTENT_ID, "children"),
        Output(GLOBAL_ENTER_ASYNC_ID, "data"),
        Output(GLOBAL_REENTER_ASYNC_ID, "data"),
        Output(GLOBAL_ROUTE_ASYNC_ID, "data"),
        Output(GLOBAL_LEAVE_ASYNC_ID, "data"),
        Input(GLOBAL_LOCATION_ID, "pathname"),
        State(GLOBAL_ROUTING_STORAGE_ID, "data"),
        State(GLOBAL_ENTER_ASYNC_ID, "data"),
        State(GLOBAL_REENTER_ASYNC_ID, "data"),
        State(GLOBAL_ROUTE_ASYNC_ID, "data"),
        State(GLOBAL_LEAVE_ASYNC_ID, "data"),
        on_init=InjectionType.Hidden
    )
    def _global_async_update_location_callback_(self, pathname, routing, enter, reenter, route, leave):
        endpoint = self.endpointize(path=pathname, relative=False)
        current = (routing or {}).get("current")
        redirect, page = self.redirect(endpoint=endpoint)
        enter, reenter, route, leave = TriggerAPI(**(enter or {})), TriggerAPI(**(reenter or {})), TriggerAPI(**(route or {})), TriggerAPI(**(leave or {}))
        if current == redirect:
            enter, reenter, route, leave = dash.no_update, reenter.trigger().dict(), route.trigger().dict(), dash.no_update
            self._log_.debug(lambda: f"Route Operation: Reentered ({redirect})")
        else:
            enter, reenter, route, leave = enter.trigger().dict(), dash.no_update, route.trigger().dict(), leave.trigger().dict()
            self._log_.info(lambda: f"Route Operation: Entered ({redirect})")
        if page:
            navigation = page._navigation_ if page._navigation_ else dash.no_update
            sidebar, content = page._sidebar_, page._content_
        else:
            navigation, sidebar, content = dash.no_update, self.GLOBAL_NOT_FOUND_LAYOUT, self.GLOBAL_NOT_FOUND_LAYOUT
            self._log_.warning(lambda: f"Route Operation: Missing ({endpoint})")
        pathname = self.anchorize(path=redirect, relative=False) if redirect != endpoint else dash.no_update
        return pathname, {"current": redirect}, navigation, sidebar, content, enter, reenter, route, leave

    @clientside_callback(
        Output(GLOBAL_SIDEBAR_COLLAPSE_ID, "is_open"),
        Input(GLOBAL_SIDEBAR_BUTTON_ID, "n_clicks"),
        State(GLOBAL_SIDEBAR_COLLAPSE_ID, "is_open"),
        on_click=InjectionType.Hidden
    )
    def _global_async_sidebar_button_callback_(self):
        return self.asset("Callbacks/Collapse.js", url=False)

    @clientside_callback(
        Output(GLOBAL_CONTACTS_COLLAPSE_ID, "is_open"),
        Output(GLOBAL_CONTACTS_ARROW_ID, "className"),
        Input(GLOBAL_CONTACTS_BUTTON_ID, "n_clicks"),
        State(GLOBAL_CONTACTS_COLLAPSE_ID, "is_open"),
        State(GLOBAL_CONTACTS_ARROW_ID, "className"),
        on_click=InjectionType.Hidden
    )
    def _global_async_contacts_button_callback_(self):
        return self.asset("Callbacks/Collapse.js", url=False)

    @clientside_callback(
        Output(GLOBAL_EMAIL_STORAGE_ID, "data"),
        Input(GLOBAL_EMAIL_STORAGE_ID, "data")
    )
    def _global_async_email_client_callback_(self):
        return self.asset("Callbacks/Email.js", url=False)

    @clientside_callback(
        Output(GLOBAL_IMPORT_UPLOAD_ID, "contents"),
        Input(GLOBAL_IMPORT_UPLOAD_ID, "contents"),
        State(GLOBAL_IMPORT_UPLOAD_ID, "filename")
    )
    def _global_async_import_snapshot_callback_(self):
        return self.asset("Callbacks/Import.js", url=False)

    @clientside_callback(
        Output(GLOBAL_EXPORT_DOWNLOAD_ID, "data"),
        Input(GLOBAL_EXPORT_ID, "n_clicks"),
        State(GLOBAL_LOCATION_ID, "pathname"),
        State({"app": dash.ALL, "page": dash.ALL, "type": dash.ALL, "name": dash.ALL, "portable": "data"}, "data"),
        State({"app": dash.ALL, "page": dash.ALL, "type": dash.ALL, "name": dash.ALL, "portable": "value"}, "value")
    )
    def _global_async_export_snapshot_callback_(self):
        return self.asset("Callbacks/Export.js", url=False)

    @clientside_callback(
        Output(GLOBAL_MEMORY_STORAGE_ID, "data"),
        on_clean_memory=InjectionType.Hidden
    )
    def _global_async_clean_memory_callback_(self):
        return self.asset("Callbacks/Clear.js", url=False)

    @clientside_callback(
        Output(GLOBAL_SESSION_STORAGE_ID, "data"),
        on_clean_session=InjectionType.Hidden
    )
    def _global_async_clean_session_callback_(self):
        return self.asset("Callbacks/Clear.js", url=False)

    @clientside_callback(
        Output(GLOBAL_LOCAL_STORAGE_ID, "data"),
        on_clean_local=InjectionType.Hidden
    )
    def _global_async_clean_local_callback_(self):
        return self.asset("Callbacks/Clear.js", url=False)

    @clientside_callback(
        Output(GLOBAL_CLEAN_MEMORY_ASYNC_ID, "data"),
        Output(GLOBAL_CLEAN_SESSION_ASYNC_ID, "data"),
        Output(GLOBAL_CLEAN_LOCAL_ASYNC_ID, "data"),
        State(GLOBAL_CLEAN_MEMORY_ASYNC_ID, "data"),
        State(GLOBAL_CLEAN_SESSION_ASYNC_ID, "data"),
        State(GLOBAL_CLEAN_LOCAL_ASYNC_ID, "data"),
        on_clean_reset=InjectionType.Hidden
    )
    def _global_async_clean_reset_callback_(self):
        return self.asset("Callbacks/Reset.js", url=False)

    @clientside_callback(
        Output(GLOBAL_MODAL_ID, "is_open"),
        Input(GLOBAL_MODAL_BUTTON_ID, "n_clicks")
    )
    def _global_async_dismiss_modal_callback_(self):
        return self.asset("Callbacks/Dismiss.js", url=False)

    @clientside_callback(
        Output(GLOBAL_THEME_STORAGE_ID, "data"),
        Input(GLOBAL_THEME_TOGGLE_ID, "n_clicks"),
        State(GLOBAL_THEME_STORAGE_ID, "data"),
        on_click=InjectionType.Hidden
    )
    def _global_async_theme_toggle_callback_(self):
        return self.asset("Callbacks/Theme.js", url=False)

    @clientside_callback(
        Output(GLOBAL_THEME_STORAGE_ID, "data"),
        Input(GLOBAL_SETTINGS_THEME_ID, "n_clicks"),
        State(GLOBAL_THEME_STORAGE_ID, "data"),
        on_click=InjectionType.Hidden
    )
    def _global_async_settings_theme_callback_(self):
        return self.asset("Callbacks/Theme.js", url=False)

    @clientside_callback(
        Output(GLOBAL_SETTINGS_THEME_ICON_ID, "className"),
        Output(GLOBAL_SETTINGS_THEME_LABEL_ID, "children"),
        Input(GLOBAL_THEME_STORAGE_ID, "data"),
        on_init=InjectionType.Hidden
    )
    def _global_async_settings_theme_display_callback_(self):
        return self.asset("Callbacks/ThemeDisplay.js", url=False)

    @clientside_callback(
        Output(GLOBAL_SETTINGS_AUTH_ICON_ID, "className"),
        Output(GLOBAL_SETTINGS_AUTH_LABEL_ID, "children"),
        Input(GLOBAL_USER_STORAGE_ID, "data"),
        on_init=InjectionType.Hidden
    )
    def _global_async_settings_auth_display_callback_(self):
        return self.asset("Callbacks/AuthDisplay.js", url=False)

    @clientside_callback(
        Output(GLOBAL_THEME_ICON_ID, "className"),
        Input(GLOBAL_THEME_STORAGE_ID, "data"),
        on_init=InjectionType.Hidden
    )
    def _global_async_theme_apply_callback_(self):
        return self.asset("Callbacks/ThemeApply.js", url=False)

    @clientside_callback(
        Output(GLOBAL_MENU_LOCK_ID, "className"),
        Output(GLOBAL_MENU_USER_ID, "children"),
        Output(GLOBAL_LOGIN_ICON_ID, "className"),
        Output(GLOBAL_LOGIN_LABEL_ID, "children"),
        Input(GLOBAL_USER_STORAGE_ID, "data"),
        on_init=InjectionType.Hidden
    )
    def _global_async_menu_user_callback_(self):
        return self.asset("Callbacks/Account.js", url=False)

    @serverside_callback(
        Output(GLOBAL_LOGIN_MODAL_ID, "is_open"),
        Output(GLOBAL_USER_STORAGE_ID, "data"),
        Input(GLOBAL_LOGIN_OPEN_ID, "n_clicks"),
        Input(GLOBAL_SETTINGS_AUTH_ID, "n_clicks"),
        Input(GLOBAL_LOGIN_SUBMIT_ID, "n_clicks"),
        Input(GLOBAL_LOGIN_PASS_ID, "n_submit"),
        State(GLOBAL_LOGIN_USER_ID, "value"),
        State(GLOBAL_LOGIN_PASS_ID, "value"),
        State(GLOBAL_USER_STORAGE_ID, "data")
    )
    def _global_async_authenticate_callback_(self, open_clicks, settings_clicks, submit_clicks, submit_enter, username, password, user):
        if dash.ctx.triggered_id == self.GLOBAL_SETTINGS_AUTH_ID and not settings_clicks:
            return dash.no_update, dash.no_update
        if dash.ctx.triggered_id in (self.GLOBAL_LOGIN_OPEN_ID, self.GLOBAL_SETTINGS_AUTH_ID):
            if user:
                self._log_.info(lambda: f"Authenticate Operation: Revoked ({user})")
                self.notify.info("Signed out", header="Session Ended")
                return False, None
            return True, user
        if (result := self.authenticate(username, password)):
            self._log_.info(lambda: f"Authenticate Operation: Granted ({result})")
            self.notify.success(f"Signed in as {result}", header="Authenticated")
            return False, result
        self._log_.warning(lambda: "Authenticate Operation: Failed · Due to Invalid Credentials")
        self.notify.error("Invalid credentials", header="Authentication Failed")
        return True, user

    def ids(self) -> None:
        pass

    def components(self) -> None:
        pass

    def pages(self) -> None:
        pass

    def authenticate(self, username: str | None, password: str | None) -> str | None:
        return username or None

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