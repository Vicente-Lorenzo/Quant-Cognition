from __future__ import annotations

import random
from typing import TYPE_CHECKING
from dash import dcc, html
import dash_bootstrap_components as dbc

from Library.App.V2.Core.Callback import Output, Input, State, InjectionType, clientside_callback
from Library.App.V2.Core.Identity import GlobalAPI
from Library.App.V2.Component.Component import Component, ButtonAPI, IconAPI, LoadingAPI, ModalAPI, StorageAPI, TextAPI
from Library.App.V2.Core.Layout import DefaultLayoutAPI
from Library.App.V2.Session import TriggerAPI

if TYPE_CHECKING:
    from Library.App.V2.Page.Page import PageAPI

class ShellAPI(GlobalAPI):

    def __init_default_layout__(self) -> None:
        self.GLOBAL_NOT_FOUND_LAYOUT = DefaultLayoutAPI(icon="bi bi-compass", title="Resource Not Found", description="Unable to find the resource you are looking for", details="Please check the URL path", classname="empty").build()
        self.GLOBAL_LOADING_LAYOUT = DefaultLayoutAPI(icon="bi bi-hourglass-split", title="Loading", description="This resource is loading its content", details="Please wait a moment", classname="loading").build()
        self.GLOBAL_MAINTENANCE_LAYOUT = DefaultLayoutAPI(icon="bi bi-tools", title="Under Maintenance", description="This resource is temporarily down for maintenance", details="Please try again later", classname="maintenance").build()
        self.GLOBAL_DEVELOPMENT_LAYOUT = DefaultLayoutAPI(icon="bi bi-cone-striped", title="Under Development", description="This resource is currently under development", details="Please try again later", classname="development").build()
        self.GLOBAL_FORBIDDEN_LAYOUT = DefaultLayoutAPI(icon="bi bi-shield-lock", title="Access Denied", description="You do not have permission to view this resource", details="Please sign in with an authorized account", classname="forbidden").build()

    def __init_header_layout__(self) -> Component:
        titles = [html.Span(self._name_, className="app-brand-name")]
        if self._team_: titles.append(html.Span(self._team_, className="app-brand-team"))
        brand = dcc.Link([html.Img(src=self.asset("Images/logo.png"), className="app-logo"), html.Div(titles, className="app-brand-titles")], href=self._endpoint_, id=self.GLOBAL_BRAND_ID, className="app-brand")
        nav = html.Div(id=self.GLOBAL_NAVIGATION_ID, className="app-nav")
        toggle = html.Button(html.I(className="bi bi-list"), id=self.GLOBAL_NAVIGATION_TOGGLE_ID, n_clicks=0, className="app-nav-toggle", **{"aria-label": "Menu"})
        return html.Header([brand, self._tip_(self.GLOBAL_BRAND_ID, "Go to Launchpad page"), nav, toggle, *self.__init_menu_layout__()], className="app-header")

    def __init_menu_layout__(self) -> list[Component]:
        settings = self.anchorize(path="/settings", relative=True)
        label = html.Span([html.I(className="bi bi-person app-account-icon app-account-public", id=self.GLOBAL_ACCOUNT_ICON_ID), html.Span("Guest", id=self.GLOBAL_MENU_USER_ID)], className="app-menu-label")
        items = [
            dbc.DropdownMenuItem([html.I(className="bi bi-box-arrow-in-right", id=self.GLOBAL_LOGIN_ICON_ID), html.Span("Sign In", id=self.GLOBAL_LOGIN_LABEL_ID)], id=self.GLOBAL_LOGIN_OPEN_ID, n_clicks=0, className="app-menu-item"),
            dbc.DropdownMenuItem([html.I(className="bi bi-moon-stars", id=self.GLOBAL_THEME_ICON_ID), html.Span("Theme")], id=self.GLOBAL_THEME_TOGGLE_ID, n_clicks=0, className="app-menu-item"),
            dbc.DropdownMenuItem(divider=True),
            dbc.DropdownMenuItem([html.I(className="bi bi-clock-history"), html.Span("Session")], id=self.GLOBAL_MENU_SESSION_ID, href=f"{settings}#session", className="app-menu-item"),
            dbc.DropdownMenuItem([html.I(className="bi bi-gear"), html.Span("Settings")], id=self.GLOBAL_MENU_SETTINGS_ID, href=settings, className="app-menu-item"),
        ]
        menu = dbc.DropdownMenu(items, label=label, align_end=True, nav=True, in_navbar=True, id=self.GLOBAL_MENU_ID, className="app-menu")
        return [menu,
                self._tip_(self.GLOBAL_MENU_ID, "Your account", placement="left"),
                self._tip_(self.GLOBAL_LOGIN_OPEN_ID, "Sign in or out of your account", placement="left"),
                self._tip_(self.GLOBAL_THEME_TOGGLE_ID, "Cycle the color theme", placement="left"),
                self._tip_(self.GLOBAL_MENU_SESSION_ID, "Edit and clean stored data", placement="left"),
                self._tip_(self.GLOBAL_MENU_SETTINGS_ID, "Open the settings page", placement="left")]

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
            *ButtonAPI(id=self.GLOBAL_SIDEBAR_BUTTON_ID, background="primary", classname="sidebar-toggle", tooltip="Toggle the sidebar", placement="top", label=[IconAPI(icon="bi bi-layout-sidebar-inset")]).build(),
            *ButtonAPI(id=self.GLOBAL_CONTACTS_BUTTON_ID, background="primary", tooltip="Show contact details", placement="top", label=[IconAPI(icon="bi bi-caret-down-fill", id=self.GLOBAL_CONTACTS_ARROW_ID), TextAPI(text=" Contacts "), IconAPI(icon="bi bi-question-circle")]).build(),
            *ButtonAPI(id=self.GLOBAL_IMPORT_ID, upload=self.GLOBAL_IMPORT_UPLOAD_ID, background="warning", tooltip="Import a session snapshot", placement="top", label=[TextAPI(text="Import "), IconAPI(icon="bi bi-upload")]).build(),
            *ButtonAPI(id=self.GLOBAL_EXPORT_ID, download=self.GLOBAL_EXPORT_DOWNLOAD_ID, background="warning", tooltip="Export a session snapshot", placement="top", label=[TextAPI(text="Export "), IconAPI(icon="bi bi-download")]).build(),
            dbc.Collapse(dbc.Card(dbc.CardBody([
                *([html.Div([html.B("Team: "), html.Span(self._team_)])] if self._team_ else []),
                *([html.Div([html.B("Contact: "), html.A(self._contact_, href=f"mailto:{self._contact_}")])] if self._contact_ else []),
                *([html.Div("No contact details available", className="settings-hint")] if not (self._team_ or self._contact_) else []),
            ]), className="panel"), id=self.GLOBAL_CONTACTS_COLLAPSE_ID, is_open=False),
        ], className="left")
        center = html.Div(html.Span(random.choice(self._mottos_), id=self.GLOBAL_MOTTO_ID, className="app-motto") if self._mottos_ else None, className="center")
        right = html.Div([
            *ButtonAPI(id=self.GLOBAL_CLEAN_RESET_BUTTON_ID, background="danger", tooltip="Clear all stored data and reload", placement="top", label=[IconAPI(icon="bi bi-trash"), TextAPI(text=" Reset ")]).build(),
        ], className="right")
        return html.Footer([left, center, right], className="app-footer")

    def __init_notification_layout__(self) -> Component:
        return html.Div(id=self.GLOBAL_NOTIFICATION_ID, className="app-notifications")

    def __init_hidden_layout__(self) -> Component:
        hidden = [dcc.Location(id=self.GLOBAL_LOCATION_ID, refresh=False)]
        hidden.extend(StorageAPI(id=self.GLOBAL_ROUTING_STORAGE_ID, persistence="memory").build())
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
        hidden.extend(StorageAPI(id=self.GLOBAL_MOTTO_ASYNC_ID, persistence="memory").build())
        hidden.extend(StorageAPI(id=self.GLOBAL_THEME_STORAGE_ID, persistence="local").build())
        hidden.extend(StorageAPI(id=self.GLOBAL_USER_STORAGE_ID, persistence="session").build())
        return html.Div(hidden, className="app-hidden")

    def __init_modal_layout__(self) -> Component:
        modal = ModalAPI(id=self.GLOBAL_MODAL_ID, size="lg", open=False, fade=False, centered=True, keyboard=True, backdrop=True, header=[html.Div(id=self.GLOBAL_MODAL_HEADER_ID)], body=[html.Div(id=self.GLOBAL_MODAL_BODY_ID)], footer=[html.Div(id=self.GLOBAL_MODAL_FOOTER_ID, style={"flex": "1"}), *ButtonAPI(id=self.GLOBAL_MODAL_BUTTON_ID, background="primary", label=[TextAPI(text="Close")]).build()]).build()
        return html.Div([*modal], className="app-modal")

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

    @staticmethod
    def _label_(page) -> list | str:
        if not page.icon: return page.button
        return [html.I(className=page.icon), html.Span(page.button)]

    @staticmethod
    def _tip_(target: dict, text: str, placement: str = "bottom") -> Component:
        return dbc.Tooltip(text, target=target, delay={"show": 500, "hide": 100}, placement=placement)

    def _init_navigation_(self) -> None:
        for endpoint, page in self._pages_.items():
            if page._navigation_: continue
            children = [child for child in page.children if not child._parametric_]
            if not page.parent and not children:
                page._navigation_ = []
                continue
            if page.parent and self._sectioned_(page):
                page._navigation_ = page.parent._navigation_
                continue
            if page.parent and not children:
                nested = self._sectioned_(page.parent) and page.parent.parent is not None
                page._navigation_ = self._navbar_(page, [page.parent], page.parent.children) if nested else page.parent._navigation_
                continue
            page._navigation_ = self._navbar_(page, page.backwards(), page.currents())
        self._log_.debug(lambda: "Navigation Operation: Composed (Family)")

    @staticmethod
    def _sectioned_(page: PageAPI) -> bool:
        from Library.App.V2.Page.Launchpad import LaunchpadAPI
        return isinstance(page, LaunchpadAPI)

    def _navbar_(self, page: PageAPI, backwards: list, currents: list) -> Component:
        links = []
        for backward in backwards:
            links.append(dbc.NavLink([html.I(className="bi bi-chevron-left"), html.Span(backward.button)], href=self.destination(backward), className="app-navlink app-navlink-back"))
        for current in currents:
            if current._parametric_: continue
            forwards = [forward for forward in page.forwards(current) if not forward._parametric_]
            if forwards and current.endpoint != page.endpoint:
                items = [dbc.DropdownMenuItem(self._label_(forward), href=self.destination(forward)) for forward in forwards]
                links.append(dbc.DropdownMenu(items, label=self._label_(current), nav=True, in_navbar=True, toggle_style={"padding": "0"}, className="app-navlink app-navlink-drop"))
            else:
                identifier = self.identify(type="navlink", name=current.endpoint)
                links.append(dbc.NavLink(self._label_(current), href=self.destination(current), active="exact", id=identifier, className="app-navlink"))
                links.append(self._tip_(identifier, f"Go to {current.button} page"))
        return dbc.Nav(links, navbar=True, className="app-nav-inner")

    @clientside_callback(
        Output(GlobalAPI.GLOBAL_NAVIGATION_ID, "className"),
        Input(GlobalAPI.GLOBAL_NAVIGATION_TOGGLE_ID, "n_clicks"),
        State(GlobalAPI.GLOBAL_NAVIGATION_ID, "className"),
        on_click=InjectionType.Hidden,
    )
    def _navigation_toggle_callback_(self):
        return self.asset("Callbacks/Menu.js", url=False)