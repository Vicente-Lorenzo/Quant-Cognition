import time
from pathlib import PurePosixPath

import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate

import flask
from fastapi import FastAPI
from fastapi.middleware.wsgi import WSGIMiddleware

from Library.App.V1 import *
from Library.Logging import *
from Library.Utility.Path import *
from Library.Utility.Typing import *
from Library.Utility.Runtime import *
from Library.Utility.File import *

class AppAPI:

    GLOBAL_LOCATION_ID: Union[ComponentID, dict] = ComponentID()
    GLOBAL_LOCATION_STORAGE_ID: Union[ComponentID, dict] = ComponentID()
    GLOBAL_DESCRIPTION_ID: Union[ComponentID, dict] = ComponentID()
    GLOBAL_NAVIGATION_ID: Union[ComponentID, dict] = ComponentID()
    GLOBAL_CONTENT_ID: Union[ComponentID, dict] = ComponentID()
    GLOBAL_CONTENT_LOADING_ID: Union[ComponentID, dict] = ComponentID()
    GLOBAL_SIDEBAR_ID: Union[ComponentID, dict] = ComponentID()
    GLOBAL_SIDEBAR_BUTTON_ID: Union[ComponentID, dict] = ComponentID()
    GLOBAL_SIDEBAR_LOADING_ID: Union[ComponentID, dict] = ComponentID()
    GLOBAL_SIDEBAR_COLLAPSE_ID: Union[ComponentID, dict] = ComponentID()

    GLOBAL_BACKWARD_BUTTON_ID: Union[ComponentID, dict] = ComponentID()
    GLOBAL_BACKWARD_ASYNC_ID: Union[ComponentID, dict] = ComponentID()
    GLOBAL_REFRESH_BUTTON_ID: Union[ComponentID, dict] = ComponentID()
    GLOBAL_REFRESH_ASYNC_ID: Union[ComponentID, dict] = ComponentID()
    GLOBAL_FORWARD_BUTTON_ID: Union[ComponentID, dict] = ComponentID()
    GLOBAL_FORWARD_ASYNC_ID: Union[ComponentID, dict] = ComponentID()

    GLOBAL_CONTACTS_ARROW_ID: Union[ComponentID, dict] = ComponentID()
    GLOBAL_CONTACTS_BUTTON_ID: Union[ComponentID, dict] = ComponentID()
    GLOBAL_CONTACTS_COLLAPSE_ID: Union[ComponentID, dict] = ComponentID()
    GLOBAL_CONTACTS_ID: Union[ComponentID, dict] = ComponentID()

    GLOBAL_IMPORT_ID: Union[ComponentID, dict] = ComponentID()
    GLOBAL_IMPORT_UPLOAD_ID: Union[ComponentID, dict] = ComponentID()
    GLOBAL_EXPORT_ID: Union[ComponentID, dict] = ComponentID()
    GLOBAL_EXPORT_DOWNLOAD_ID: Union[ComponentID, dict] = ComponentID()

    GLOBAL_NOTIFICATION_ID: Union[ComponentID, dict] = ComponentID()

    GLOBAL_ENTER_ASYNC_ID: Union[ComponentID, dict] = ComponentID()
    GLOBAL_REENTER_ASYNC_ID: Union[ComponentID, dict] = ComponentID()
    GLOBAL_ROUTE_ASYNC_ID: Union[ComponentID, dict] = ComponentID()
    GLOBAL_LEAVE_ASYNC_ID: Union[ComponentID, dict] = ComponentID()
    GLOBAL_ROUTING_STORAGE_ID: Union[ComponentID, dict] = ComponentID()

    GLOBAL_MEMORY_STORAGE_ID: Union[ComponentID, dict] = ComponentID()
    GLOBAL_SESSION_STORAGE_ID: Union[ComponentID, dict] = ComponentID()
    GLOBAL_LOCAL_STORAGE_ID: Union[ComponentID, dict] = ComponentID()

    GLOBAL_CLEAN_MEMORY_BUTTON_ID: Union[ComponentID, dict] = ComponentID()
    GLOBAL_CLEAN_MEMORY_ASYNC_ID: Union[ComponentID, dict] = ComponentID()
    GLOBAL_CLEAN_SESSION_BUTTON_ID: Union[ComponentID, dict] = ComponentID()
    GLOBAL_CLEAN_SESSION_ASYNC_ID: Union[ComponentID, dict] = ComponentID()
    GLOBAL_CLEAN_LOCAL_BUTTON_ID: Union[ComponentID, dict] = ComponentID()
    GLOBAL_CLEAN_LOCAL_ASYNC_ID: Union[ComponentID, dict] = ComponentID()
    GLOBAL_CLEAN_RESET_BUTTON_ID: Union[ComponentID, dict] = ComponentID()
    GLOBAL_CLEAN_RESET_ASYNC_ID: Union[ComponentID, dict] = ComponentID()

    GLOBAL_MODAL_ID: Union[ComponentID, dict] = ComponentID()
    GLOBAL_MODAL_HEADER_ID: Union[ComponentID, dict] = ComponentID()
    GLOBAL_MODAL_BODY_ID: Union[ComponentID, dict] = ComponentID()
    GLOBAL_MODAL_FOOTER_ID: Union[ComponentID, dict] = ComponentID()
    GLOBAL_MODAL_BUTTON_ID: Union[ComponentID, dict] = ComponentID()

    GLOBAL_EMAIL_STORAGE_ID: Union[ComponentID, dict] = ComponentID()

    GLOBAL_HIGH_FREQUENCY_INTERVAL_ID: Union[ComponentID, dict] = ComponentID()
    GLOBAL_MEDIUM_FREQUENCY_INTERVAL_ID: Union[ComponentID, dict] = ComponentID()
    GLOBAL_LOW_FREQUENCY_INTERVAL_ID: Union[ComponentID, dict] = ComponentID()

    GLOBAL_NOT_FOUND_LAYOUT: Component
    GLOBAL_LOADING_LAYOUT: Component
    GLOBAL_MAINTENANCE_LAYOUT: Component
    GLOBAL_DEVELOPMENT_LAYOUT: Component
    GLOBAL_NOT_INDEXED_LAYOUT: Component

    def __init__(self, *,
                 name: str = "<Insert App Name>",
                 title: str = "<Insert App Title>",
                 team: str = "<Insert Team Name>",
                 description: str = None,
                 contact: str = "<Insert Contact Email>",
                 update: str = "",
                 protocol: str = None,
                 host: str = None,
                 port: int = None,
                 domain: str = None,
                 proxy: str = None,
                 anchor: str = None,
                 debug: bool = False,
                 notification_limit: int = 10,
                 notification_duration: Union[int, None] = 5000,
                 notification_dismissable: bool = True,
                 notification_persistence: Union[bool, str] = None,
                 high_frequency_interval: int = 1000,
                 medium_frequency_interval: int = 60 * 1000,
                 low_frequency_interval: int = 60 * 60 * 1000) -> None:

        self._log_ = LoggingAPI()

        self._name_: str = name
        self._log_.debug(lambda: f"Defined Name = {self._name_}")
        self._title_: str = title
        self._log_.debug(lambda: f"Defined Title = {self._title_}")
        self._team_: str = team
        self._log_.debug(lambda: f"Defined Team = {self._team_}")
        self._description_: str = description
        self._log_.debug(lambda: f"Defined Description = {self._description_}")
        self._contact_: str = contact
        self._log_.debug(lambda: f"Defined Contact = {self._contact_}")
        self._update_: str = update
        self._log_.debug(lambda: f"Defined Update = {self._update_}")

        host: str = host or "localhost"
        self._host_: str = inspect_file_path(host, builder=PurePosixPath)
        self._log_.debug(lambda: f"Defined Host = {self._host_}")
        self._port_: int = port or find_host_port(host=self._host_, port_min=8050)
        self._log_.debug(lambda: f"Defined Port = {self._port_}")

        protocol: str = protocol or "http"
        self._protocol_: str = inspect_file_path(protocol, builder=PurePosixPath)
        self._log_.debug(lambda: f"Defined Protocol = {self._protocol_}")

        host_address: str = f"{self._host_}:{self._port_}"
        self._host_address_: str = inspect_file_path(host_address, builder=PurePosixPath)
        self._log_.debug(lambda: f"Defined Host Address = {self._host_address_}")
        self._host_url_: str = f"{self._protocol_}://{self._host_address_}"
        self._log_.debug(lambda: f"Defined Host URL = {self._host_url_}")

        domain_address: str = domain or self._host_address_
        self._domain_address_: str = inspect_file_path(domain_address, builder=PurePosixPath)
        self._log_.debug(lambda: f"Defined Domain Address = {self._domain_address_}")
        self._domain_url_: str = f"{self._protocol_}://{self._domain_address_}"
        self._log_.debug(lambda: f"Defined Domain URL = {self._domain_url_}")

        self._proxy_: str = proxy or f"{self._host_url_}::{self._domain_url_}"
        self._log_.debug(lambda: f"Defined Proxy = {self._proxy_}")

        anchor: str = anchor or "/"
        self._anchor_: PurePath = inspect_file(anchor, header=True, builder=PurePosixPath)
        self._log_.debug(lambda: f"Defined Anchor = {self._anchor_}")
        self._endpoint_: str = inspect_file_path(anchor, header=True, footer=True, builder=PurePosixPath)
        self._log_.debug(lambda: f"Defined Endpoint = {self._endpoint_}")

        self._library_: Path = traceback_current_module(resolve=True)
        self._log_.debug(lambda: f"Defined Library = {self._library_}")
        self._library_assets_: Path = self._library_ / "Assets"
        self._log_.debug(lambda: f"Defined Library Assets = {self._library_assets_}")
        self._library_assets_url_: str = "_library_"
        self._log_.debug(lambda: f"Defined Library Assets URL = {self._library_assets_url_}")
        self._application_: Path = traceback_calling_module(resolve=True)
        self._log_.debug(lambda: f"Defined Application = {self._application_}")
        self._application_assets_: Path = self._application_ / "Assets"
        self._log_.debug(lambda: f"Defined Application Assets = {self._application_assets_}")
        self._application_assets_url_: str = "_application_"
        self._log_.debug(lambda: f"Defined Application Assets URL = {self._application_assets_url_}")

        self._debug_: bool = debug
        self._log_.debug(lambda: f"Defined Debug = {self._debug_}")
        self._notification_limit_: int = notification_limit
        self._log_.debug(lambda: f"Defined Notification Limit = {self._notification_limit_}")
        self._notification_duration_: Union[int, None] = notification_duration
        self._log_.debug(lambda: f"Defined Notification Duration = {self._notification_duration_}")
        self._notification_dismissable_: bool = notification_dismissable
        self._log_.debug(lambda: f"Defined Notification Dismissable = {self._notification_dismissable_}")
        self._notification_persistence_: Union[bool, str] = notification_persistence
        self._log_.debug(lambda: f"Defined Notification Persistence = {self._notification_persistence_}")

        self._high_frequency_interval_: int = high_frequency_interval
        self._log_.debug(lambda: f"Defined High Frequency Interval = {self._high_frequency_interval_}")
        self._medium_frequency_interval_: int = medium_frequency_interval
        self._log_.debug(lambda: f"Defined Medium Frequency Interval = {self._medium_frequency_interval_}")
        self._low_frequency_interval_: int = low_frequency_interval
        self._log_.debug(lambda: f"Defined Low Frequency Interval = {self._low_frequency_interval_}")

        self._init_app_()
        self._log_.info(lambda: "Initialized App")

        self._init_layout_()
        self._log_.info(lambda: "Initialized Layout")

        self._init_pages_()
        self._log_.info(lambda: "Initialized Pages")

        self._init_navigation_()
        self._log_.info(lambda: "Initialized Navigation")

        self._init_callbacks_()
        self._log_.info(lambda: "Initialized Callbacks")

        self._init_notifications_()
        self._log_.info(lambda: "Initialized Notifications")

    def __init_ids__(self) -> None:
        self._ids_: set = set()
        self.GLOBAL_LOCATION_ID: dict = self.register(type="location", name="location")
        self.GLOBAL_LOCATION_STORAGE_ID: dict = self.register(type="storage", name="location")
        self.GLOBAL_DESCRIPTION_ID: dict = self.register(type="div", name="description")
        self.GLOBAL_NAVIGATION_ID: dict = self.register(type="navigator", name="navigation")
        self.GLOBAL_CONTENT_ID: dict = self.register(type="div", name="content")
        self.GLOBAL_CONTENT_LOADING_ID: dict = self.register(type="loading", name="content")
        self.GLOBAL_SIDEBAR_ID: dict = self.register(type="div", name="sidebar")
        self.GLOBAL_SIDEBAR_BUTTON_ID: dict = self.register(type="button", name="sidebar")
        self.GLOBAL_SIDEBAR_LOADING_ID: dict = self.register(type="loading", name="sidebar")
        self.GLOBAL_SIDEBAR_COLLAPSE_ID: dict = self.register(type="collapse", name="sidebar")

        self.GLOBAL_BACKWARD_BUTTON_ID: dict = self.register(type="button", name="backward")
        self.GLOBAL_BACKWARD_ASYNC_ID: dict = self.register(type="asyncer", name="backward")
        self.GLOBAL_REFRESH_BUTTON_ID: dict = self.register(type="button", name="refresh")
        self.GLOBAL_REFRESH_ASYNC_ID: dict = self.register(type="asyncer", name="refresh")
        self.GLOBAL_FORWARD_BUTTON_ID: dict = self.register(type="button", name="forward")
        self.GLOBAL_FORWARD_ASYNC_ID: dict = self.register(type="asyncer", name="forward")

        self.GLOBAL_CONTACTS_ARROW_ID: dict = self.register(type="icon", name="contacts")
        self.GLOBAL_CONTACTS_BUTTON_ID: dict = self.register(type="button", name="contacts")
        self.GLOBAL_CONTACTS_COLLAPSE_ID: dict = self.register(type="collapse", name="contacts")
        self.GLOBAL_CONTACTS_ID: dict = self.register(type="card", name="contacts")

        self.GLOBAL_IMPORT_ID: dict = self.register(type="button", name="import")
        self.GLOBAL_IMPORT_UPLOAD_ID: dict = self.register(type="upload", name="import")
        self.GLOBAL_EXPORT_ID: dict = self.register(type="button", name="export")
        self.GLOBAL_EXPORT_DOWNLOAD_ID: dict = self.register(type="download", name="export")

        self.GLOBAL_NOTIFICATION_ID: dict = self.register(type="div", name="notification")

        self.GLOBAL_ENTER_ASYNC_ID: dict = self.register(type="asyncer", name="enter")
        self.GLOBAL_REENTER_ASYNC_ID: dict = self.register(type="asyncer", name="reenter")
        self.GLOBAL_ROUTE_ASYNC_ID: dict = self.register(type="asyncer", name="route")
        self.GLOBAL_LEAVE_ASYNC_ID: dict = self.register(type="asyncer", name="leave")
        self.GLOBAL_ROUTING_STORAGE_ID: dict = self.register(type="storage", name="routing")

        self.GLOBAL_MEMORY_STORAGE_ID: dict = self.register(type="storage", name="memory", portable="data")
        self.GLOBAL_SESSION_STORAGE_ID: dict = self.register(type="storage", name="session", portable="data")
        self.GLOBAL_LOCAL_STORAGE_ID: dict = self.register(type="storage", name="local", portable="data")

        self.GLOBAL_CLEAN_MEMORY_BUTTON_ID: dict = self.register(type="button", name="memory")
        self.GLOBAL_CLEAN_MEMORY_ASYNC_ID: dict = self.register(type="asyncer", name="memory")
        self.GLOBAL_CLEAN_SESSION_BUTTON_ID: dict = self.register(type="button", name="session")
        self.GLOBAL_CLEAN_SESSION_ASYNC_ID: dict = self.register(type="asyncer", name="session")
        self.GLOBAL_CLEAN_LOCAL_BUTTON_ID: dict = self.register(type="button", name="local")
        self.GLOBAL_CLEAN_LOCAL_ASYNC_ID: dict = self.register(type="asyncer", name="local")
        self.GLOBAL_CLEAN_RESET_BUTTON_ID: dict = self.register(type="button", name="reset")
        self.GLOBAL_CLEAN_RESET_ASYNC_ID: dict = self.register(type="asyncer", name="reset")

        self.GLOBAL_MODAL_ID: dict = self.register(type="modal", name="global")
        self.GLOBAL_MODAL_HEADER_ID: dict = self.register(type="div", name="modal_header")
        self.GLOBAL_MODAL_BODY_ID: dict = self.register(type="div", name="modal_body")
        self.GLOBAL_MODAL_FOOTER_ID: dict = self.register(type="div", name="modal_footer")
        self.GLOBAL_MODAL_BUTTON_ID: dict = self.register(type="button", name="modal_close")

        self.GLOBAL_EMAIL_STORAGE_ID: dict = self.register(type="storage", name="email")

        self.GLOBAL_HIGH_FREQUENCY_INTERVAL_ID: dict = self.register(type="interval", name="high")
        self.GLOBAL_MEDIUM_FREQUENCY_INTERVAL_ID: dict = self.register(type="interval", name="medium")
        self.GLOBAL_LOW_FREQUENCY_INTERVAL_ID: dict = self.register(type="interval", name="low")

        self.ids()

    def __init_stylesheets__(self) -> list[str]:
        stylesheets = [dbc.themes.BOOTSTRAP, dbc.icons.BOOTSTRAP]
        if self._application_assets_.exists():
            for css_file in sorted(self._application_assets_.rglob("*.css")):
                rel_path = css_file.relative_to(self._application_assets_).as_posix()
                stylesheets.append(self.asset(path=rel_path, url=True))
                self._log_.debug(lambda p=rel_path: f"Init Stylesheets: Caching Stylesheet = {p}")
        return stylesheets

    def __init_scripts__(self) -> list[str]:
        scripts = []
        if self._application_assets_.exists():
            for js_file in sorted(self._application_assets_.rglob("*.js")):
                rel_path = js_file.relative_to(self._application_assets_).as_posix()
                scripts.append(self.asset(path=rel_path, url=True))
                self._log_.debug(lambda p=rel_path: f"Init Scripts: Caching Script = {p}")
        return scripts

    def __init_assets__(self):
        def serve_application(filename: str):
            return flask.send_from_directory(self._application_assets_, filename)
        self.app.server.add_url_rule(
            rule=f"{(self._anchor_ / self._application_assets_url_).as_posix()}/<path:filename>",
            endpoint=f"_{self._application_assets_url_}_{id(self)}",
            view_func=serve_application
        )

    def _init_app_(self) -> None:
        self.app = dash.Dash(
            name=self._name_,
            title=self._title_,
            update_title=self._update_,
            routes_pathname_prefix=self._endpoint_,
            requests_pathname_prefix=self._endpoint_,
            assets_url_path=self._library_assets_url_,
            assets_folder=inspect_path(self._library_assets_),
            suppress_callback_exceptions=True,
            prevent_initial_callbacks=True
        )
        self._log_.debug(lambda: "Init App: Loaded App")
        stylesheets = self.__init_stylesheets__()
        self.app.config.external_stylesheets = stylesheets
        self._log_.debug(lambda: "Init App: Loaded Stylesheets")
        scripts = self.__init_scripts__()
        self.app.config.external_scripts = scripts
        self._log_.debug(lambda: "Init App: Loaded Scripts")
        self.__init_ids__()
        self._log_.debug(lambda: "Init App: Loaded IDs")
        self.__init_assets__()
        self._log_.debug(lambda: "Init App: Loaded Assets")

    def __init_default_layout__(self):
        self.GLOBAL_NOT_FOUND_LAYOUT = DefaultLayoutAPI(
            image=self.asset(path="Images/404.png", url=True),
            title="Resource Not Found",
            description="Unable to find the resource you are looking for.",
            details="Please check the url path.",
            classname="empty"
        ).build()
        self.GLOBAL_LOADING_LAYOUT = DefaultLayoutAPI(
            image=self.asset(path="Images/loading.gif", url=True),
            title="Loading...",
            description="This resource is loading its content.",
            details="Please wait a moment.",
            classname="loading"
        ).build()
        self.GLOBAL_MAINTENANCE_LAYOUT = DefaultLayoutAPI(
            image=self.asset(path="Images/maintenance.png", url=True),
            title="Resource Under Maintenance",
            description="This resource is temporarily down for maintenance.",
            details="Please try again later.",
            classname="maintenance"
        ).build()
        self.GLOBAL_DEVELOPMENT_LAYOUT = DefaultLayoutAPI(
            image=self.asset(path="Images/development.png", url=True),
            title="Resource Under Development",
            description="This resource is currently under development.",
            details="Please try again later.",
            classname="development"
        ).build()
        self.GLOBAL_NOT_INDEXED_LAYOUT = DefaultLayoutAPI(
            image=self.asset(path="Images/indexed.png", url=True),
            title="Resource Not Indexed",
            description="This resource is not indexed at any page.",
            details="Please try again later.",
            classname="empty"
        ).build()

    def __init_header_layout__(self) -> Component:
        return html.Div(children=[
            html.Div(children=[
                html.Div(children=[html.Img(src=self.asset(path="Images/logo.png", url=True), className="image")], className="logo"),
                html.Div(children=[html.H1(self._name_, className="title"), html.H4(self._team_, className="team")], className="titles"),
                html.Div(children=[self._description_], id=self.GLOBAL_DESCRIPTION_ID, className="description")
            ], className="information"),
            html.Div(children=[
                html.Div(children=[
                ], className="navigation", id=self.GLOBAL_NAVIGATION_ID),
                html.Div(children=[
                    *ButtonContainerAPI(elements=[
                        ButtonAPI(id=self.GLOBAL_BACKWARD_BUTTON_ID, label=[IconAPI(icon="bi bi-arrow-left")], asyncer=self.GLOBAL_BACKWARD_ASYNC_ID),
                        ButtonAPI(id=self.GLOBAL_REFRESH_BUTTON_ID, label=[IconAPI(icon="bi bi-arrow-repeat")], asyncer=self.GLOBAL_REFRESH_ASYNC_ID),
                        ButtonAPI(id=self.GLOBAL_FORWARD_BUTTON_ID, label=[IconAPI(icon="bi bi-arrow-right")], asyncer=self.GLOBAL_FORWARD_ASYNC_ID)
                    ], background="primary").build()
                ], className="location")
            ], className="controls")
        ], className="header")

    def __init_body_layout__(self) -> Component:
        return html.Div(children=[
                dbc.Collapse(children=[
                    html.Div(children=[
                        html.Div(children=[
                            self.GLOBAL_LOADING_LAYOUT
                        ], id=self.GLOBAL_SIDEBAR_ID, className="page"),
                        *LoadingAPI(id=self.GLOBAL_SIDEBAR_LOADING_ID, hidden=True).build()
                    ], className="sidebar")
                ], id=self.GLOBAL_SIDEBAR_COLLAPSE_ID, is_open=False, className="collapse"),
                html.Div(children=[
                    html.Div(children=[
                        self.GLOBAL_LOADING_LAYOUT
                    ], id=self.GLOBAL_CONTENT_ID, className="page"),
                    *LoadingAPI(id=self.GLOBAL_CONTENT_LOADING_ID, hidden=True).build()
                ], className="content"),
        ], className="body")

    def __init_footer_layout__(self) -> Component:
        return html.Div(children=[
            html.Div(children=[
                *ButtonAPI(
                    id=self.GLOBAL_SIDEBAR_BUTTON_ID, background="primary",
                    label=[IconAPI(icon="bi bi-layout-sidebar-inset")]
                ).build(),
                *ButtonAPI(
                    id=self.GLOBAL_CONTACTS_BUTTON_ID, background="primary",
                    label=[IconAPI(icon="bi bi-caret-down-fill", id=self.GLOBAL_CONTACTS_ARROW_ID), TextAPI(text="  Contacts  "), IconAPI(icon="bi bi-question-circle")]
                ).build(),
                *ButtonAPI(
                    id=self.GLOBAL_IMPORT_ID, upload=self.GLOBAL_IMPORT_UPLOAD_ID, background="warning",
                    label=[TextAPI(text="Import Snapshot  "), IconAPI(icon="bi bi-upload")]
                ).build(),
                *ButtonAPI(
                    id=self.GLOBAL_EXPORT_ID, download=self.GLOBAL_EXPORT_DOWNLOAD_ID, background="warning",
                    label=[TextAPI(text="Export Snapshot  "), IconAPI(icon="bi bi-download")]
                ).build(),
                dbc.Collapse(dbc.Card(dbc.CardBody([
                    html.Div(children=[html.B("Team: "), html.Span(self._team_)]),
                    html.Div(children=[html.B("Contact: "), html.A(self._contact_, href=f"mailto:{self._contact_}")])
                ]), className="panel"), id=self.GLOBAL_CONTACTS_COLLAPSE_ID, is_open=False)
            ], className="left"),
            html.Div(children=[
                *ButtonAPI(
                    id=self.GLOBAL_CLEAN_MEMORY_BUTTON_ID, background="danger",
                    label=[IconAPI(icon="bi bi-eraser-fill"), TextAPI(text="  Clean Memory  ")],
                    asyncer=self.GLOBAL_CLEAN_MEMORY_ASYNC_ID
                ).build(),
                *ButtonAPI(
                    id=self.GLOBAL_CLEAN_SESSION_BUTTON_ID, background="danger",
                    label=[IconAPI(icon="bi bi-eraser-fill"), TextAPI(text="  Clean Session  ")],
                    asyncer=self.GLOBAL_CLEAN_SESSION_ASYNC_ID
                ).build(),
                *ButtonAPI(
                    id=self.GLOBAL_CLEAN_LOCAL_BUTTON_ID, background="danger",
                    label=[IconAPI(icon="bi bi-eraser-fill"), TextAPI(text="  Clean Local  ")],
                    asyncer=self.GLOBAL_CLEAN_LOCAL_ASYNC_ID
                ).build(),
                *ButtonAPI(
                    id=self.GLOBAL_CLEAN_RESET_BUTTON_ID, background="danger",
                    label=[IconAPI(icon="bi bi-trash"), TextAPI(text="  Clean & Reset  ")],
                    asyncer=self.GLOBAL_CLEAN_RESET_ASYNC_ID
                ).build(),
            ], className="right"),
        ], className="footer")

    def __init_notification_layout__(self) -> Component:
        return html.Div(
            id=self.GLOBAL_NOTIFICATION_ID,
            className="notifications"
        )

    def __init_hidden_layout__(self) -> Component:
        hidden: list = [dcc.Location(id=self.GLOBAL_LOCATION_ID, refresh=False)]
        hidden.extend(StorageAPI(id=self.GLOBAL_LOCATION_STORAGE_ID, persistence="session").build())
        hidden.extend(StorageAPI(id=self.GLOBAL_ENTER_ASYNC_ID, persistence="memory").build())
        hidden.extend(StorageAPI(id=self.GLOBAL_REENTER_ASYNC_ID, persistence="memory").build())
        hidden.extend(StorageAPI(id=self.GLOBAL_ROUTE_ASYNC_ID, persistence="memory").build())
        hidden.extend(StorageAPI(id=self.GLOBAL_LEAVE_ASYNC_ID, persistence="memory").build())
        hidden.extend(StorageAPI(id=self.GLOBAL_ROUTING_STORAGE_ID, persistence="memory").build())
        hidden.extend(StorageAPI(id=self.GLOBAL_MEMORY_STORAGE_ID, persistence="memory").build())
        hidden.extend(StorageAPI(id=self.GLOBAL_SESSION_STORAGE_ID, persistence="session").build())
        hidden.extend(StorageAPI(id=self.GLOBAL_LOCAL_STORAGE_ID, persistence="local").build())
        hidden.extend(StorageAPI(id=self.GLOBAL_EMAIL_STORAGE_ID, persistence="memory").build())
        hidden.extend(IntervalAPI(id=self.GLOBAL_HIGH_FREQUENCY_INTERVAL_ID, interval=self._high_frequency_interval_).build())
        hidden.extend(IntervalAPI(id=self.GLOBAL_MEDIUM_FREQUENCY_INTERVAL_ID, interval=self._medium_frequency_interval_).build())
        hidden.extend(IntervalAPI(id=self.GLOBAL_LOW_FREQUENCY_INTERVAL_ID, interval=self._low_frequency_interval_).build())
        return html.Div(children=hidden, className="hidden")

    def __init_modal_layout__(self) -> Component:
        return html.Div(children=ModalAPI(
            id=self.GLOBAL_MODAL_ID,
            size="lg",
            open=False,
            fade=False,
            centered=True,
            keyboard=True,
            backdrop=True,
            header=[
                html.Div(id=self.GLOBAL_MODAL_HEADER_ID)
            ],
            body=[
                html.Div(id=self.GLOBAL_MODAL_BODY_ID)
            ],
            footer=[
                html.Div(id=self.GLOBAL_MODAL_FOOTER_ID, style={"flex": "1"}),
                *ButtonAPI(id=self.GLOBAL_MODAL_BUTTON_ID, label=[TextAPI(text="Close")], background="primary").build()
            ]
        ).build(), className="modal")

    def _init_layout_(self) -> None:
        self.components()
        self._log_.debug(lambda: "Init Layout: Loaded Components")
        self.__init_default_layout__()
        self._log_.debug(lambda: "Init Pages: Loaded Default Layout")
        header = self.__init_header_layout__()
        self._log_.debug(lambda: "Init Layout: Loaded Header Layout")
        body = self.__init_body_layout__()
        self._log_.debug(lambda: "Init Layout: Loaded Body Layout")
        footer = self.__init_footer_layout__()
        self._log_.debug(lambda: "Init Layout: Loaded Footer Layout")
        notification = self.__init_notification_layout__()
        self._log_.debug(lambda: "Init Layout: Loaded Notification Layout")
        hidden = self.__init_hidden_layout__()
        self._log_.debug(lambda: "Init Layout: Loaded Hidden Layout")
        modal = self.__init_modal_layout__()
        self._log_.debug(lambda: "Init Layout: Loaded Modal Layout")
        layout = html.Div(children=[header, body, footer, notification, hidden, modal], className="app")
        self.app.layout = layout
        self._log_.debug(lambda: "Init Layout: Loaded App Layout")

    def _init_pages_(self) -> None:
        self._pages_: dict[str, PageAPI] = {}
        self.pages()
        self._log_.debug(lambda: "Init Pages: Loaded Custom Pages")

    def _init_navigation_(self) -> None:
        for endpoint, page in self._pages_.items():
            if page._navigation_ or getattr(page.navigation, "__func__", None) is not PageAPI.navigation:
                self._log_.debug(lambda: f"Init Navigation: Preserving Custom Navigation for {endpoint}")
                continue
            if not page.parent and not page.children:
                page._navigation_ = []
                self._log_.debug(lambda: f"Init Navigation: Loaded Page = {endpoint} with No Navigation")
                continue
            if page.parent and not page.children:
                page._navigation_ = page.parent._navigation_
                self._log_.debug(lambda: f"Init Navigation: Loaded Page = {endpoint} with Parent Navigation")
                continue
            currents = []
            for b in page.backwards():
                backward = PaginatorAPI(
                    href=b.endpoint,
                    label=[IconAPI(icon="bi bi-arrow-bar-left"), TextAPI(text=f"  {b.button}")],
                    background="white",
                    outline_color="black",
                    outline_style="solid",
                    outline_width="1px",
                )
                currents.append(NavigatorAPI(element=backward, typename="header-navigation"))
            for c in page.currents():
                forwards = []
                for f in page.forwards(c):
                    forward = PaginatorAPI(
                        href=f.endpoint,
                        label=[TextAPI(text=f.button)],
                        background="white"
                    )
                    forwards.append(DropdownAPI(element=forward))
                dropdown = DropdownContainerAPI(
                    elements=forwards,
                    background="white",
                    align_end=True
                ) if forwards else None
                current = PaginatorAPI(
                    href=c.endpoint,
                    label=[TextAPI(text=c.button)],
                    dropdown=dropdown,
                    background="white",
                    outline_color="black",
                    outline_style="solid",
                    outline_width="1px",
                )
                currents.append(NavigatorAPI(element=current, typename="header-navigation"))
            page._navigation_ = NavigatorContainerAPI(elements=currents).build()

    def __register_callback__(self, context, func, name, is_page):
        is_client = getattr(func, "js", False)
        args = list(getattr(func, "args", []))
        kwargs = getattr(func, "kwargs", {})
        target = getattr(context, name)() if is_client else getattr(context, name)
        running_extras = []
        cancel_extras = []
        for injection in self._injector_.match(func):
            mode = getattr(func, injection.flag, False)
            mode = InjectionType.coerce(mode, injection.default)
            if mode is not InjectionType.Disabled:
                injection.register(page=context.endpoint if is_page else None)
                running_extras.extend(injection.running())
                cancel_extras.extend(injection.cancel())
                py, js = injection(app=self, is_page=is_page)
                extras = injection.args(is_page)
                inject_func = js if is_client else py
                if is_client:
                    target, args = inject_clientside_callback(
                        mode=mode,
                        injected_func=inject_func,
                        injected_args=extras,
                        original_js=target,
                        original_args=args
                    )
                else:
                    target, args = inject_serverside_callback(
                        mode=mode,
                        injected_func=inject_func,
                        injected_args=extras,
                        original_func=target,
                        original_args=args
                    )
        for attr in ["running", "cancel", "progress", "interval", "progress_default"]:
            val = getattr(func, attr, None)
            if attr == "running" and running_extras:
                val = (val or []) + running_extras
            elif attr == "cancel" and cancel_extras:
                val = (val or []) + cancel_extras
            if val is not None:
                if attr == "running":
                    kwargs[attr] = [
                        (i[0].build(context), i[1], i[2]) if isinstance(i, (list, tuple)) and len(i) == 3 and isinstance(i[0], Trigger) else i
                        for i in val
                    ]
                elif attr in ["cancel", "progress"] and isinstance(val, list):
                    kwargs[attr] = [i.build(context) if isinstance(i, Trigger) else i for i in val]
                elif isinstance(val, Trigger):
                    kwargs[attr] = val.build(context)
                else:
                    kwargs[attr] = val
        args = [a.build(context=context) if isinstance(a, Trigger) else a for a in args]
        if is_client:
            self.app.clientside_callback(target, *args, **kwargs)
            self._log_.info(lambda: f"Init Callbacks: Loaded Client-Side Callback: {name}")
        else:
            self.app.callback(*args, **kwargs)(target)
            self._log_.info(lambda: f"Init Callbacks: Loaded Server-Side Callback: {name}")

    def __register_callbacks__(self):
        for context in [self] + list(self._pages_.values()):
            is_page = isinstance(context, PageAPI)
            processed = set()
            for cls in getmro(context):
                if cls is object: continue
                for name, func in cls.__dict__.items():
                    if name in processed or not iscallable(func) or not getattr(func, "callback", False):
                        continue
                    processed.add(name)
                    self.__register_callback__(context, func, name, is_page)

    def _init_callbacks_(self) -> None:
        self._injector_ = InjectorAPI(self)
        self._log_.debug(lambda: "Init Callbacks: Loaded Injector")
        self.__register_callbacks__()
        self._log_.debug(lambda: "Init Callbacks: Loaded Callbacks")

    def _init_notifications_(self) -> None:
        self.notify = NotifierAPI(
            duration=self._notification_duration_,
            dismissable=self._notification_dismissable_,
            persistence=self._notification_persistence_
        )
        self._log_.debug(lambda: "Init Notifications: Loaded Notifier")

    def asset(self, *, path: str, url: bool = True) -> str:
        def read_content(file_path: Path) -> str:
            if file_path.suffix.lower() in [".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".webp"]:
                import base64
                suffix = file_path.suffix.lower().strip(".")
                if suffix == "jpg": suffix = "jpeg"
                elif suffix == "svg": suffix = "svg+xml"
                mime_type = f"image/{suffix}"
                encoded = base64.b64encode(file_path.read_bytes()).decode("utf-8")
                return f"data:{mime_type};base64,{encoded}"
            return str(FileAPI(file_path, encoding="utf-8"))
        if (self._library_assets_ / path).exists():
            self._log_.debug(lambda: f"Resolve Asset: Asset Found = {path} (Library)")
            if url:
                return self.app.get_asset_url(path)
            else:
                return read_content(self._library_assets_ / path)
        if (self._application_assets_ / path).exists():
            self._log_.debug(lambda: f"Resolve Asset: Asset Found = {path} (Application)")
            if url:
                return (self._anchor_ / self._application_assets_url_ / path).as_posix()
            else:
                return read_content(self._application_assets_ / path)
        raise RuntimeError(f"Resolve Asset: Asset Not Found: {path}")

    def identify(self, *, page: str = None, type: str, name: str, portable: str = "", **kwargs) -> dict:
        page = page or "global"
        cid = {"app": self.__class__.__name__, "page": page, "type": type, "name": name, "portable": portable, **kwargs}
        self._log_.debug(lambda: f"Identify Component: Identified Component = {cid}")
        return cid

    def register(self, *, page: str = "global", type: str, name: str, portable: str = "", **kwargs) -> dict:
        cid = self.identify(page=page, type=type, name=name, portable=portable, **kwargs)
        key = (cid["app"], cid["page"], cid["type"], cid["name"], cid["portable"])
        if key not in self._ids_:
            self._ids_.add(key)
            self._log_.debug(lambda: f"Register Component: Registered Component = {cid}")
            return cid
        raise RuntimeError(f"Duplicate Dash ID detected: {cid}")

    def resolve(self, *, path: Union[PurePath, str], relative: bool, footer: bool = None) -> str:
        path = inspect_file(path, header=False, builder=PurePosixPath)
        self._log_.debug(lambda: f"Resolve Path: Received = {path}")
        path = self._anchor_ / path if relative else path
        resolve = inspect_file_path(path, header=True, footer=footer, builder=PurePosixPath)
        self._log_.debug(lambda: f"Resolve Path: Resolved = {resolve}")
        return resolve

    def anchorize(self, *, path: Union[PurePath, str], relative: bool = True) -> str:
        anchor = self.resolve(path=path, relative=relative, footer=False)
        self._log_.debug(lambda: f"Anchorize Path: Resolved = {anchor}")
        return anchor

    def endpointize(self, *, path: Union[PurePath, str], relative: bool = True) -> str:
        endpoint = self.resolve(path=path, relative=relative, footer=True)
        self._log_.debug(lambda: f"Endpointize Path: Resolved = {endpoint}")
        return endpoint

    def locate(self, *, endpoint: str) -> tuple[str, PageAPI | None]:
        page = self._pages_.get(endpoint, None)
        self._log_.debug(lambda: f"Locate Page: {'Found' if page else 'Not Found'} = {endpoint}")
        return endpoint, page

    def redirect(self, *, endpoint: str) -> tuple[str, PageAPI | None]:
        endpoint, page = self.locate(endpoint=endpoint)
        while page and page.endpoint != page.redirect:
            self._log_.debug(lambda: f"Redirect Page: Redirect = {page.endpoint} -> {page.redirect}")
            endpoint, page = self.locate(endpoint=page.redirect)
        return endpoint, page

    def index(self, *, endpoint: str, page: PageAPI) -> None:
        self._pages_[endpoint] = page
        self._log_.debug(lambda: f"Index Page: Indexed = {endpoint}")

    def link(self, page: PageAPI) -> None:
        relative_path = inspect_file(page.path, header=True, builder=PurePosixPath)
        self._log_.debug(lambda: f"Page Linking: Relative Path = {relative_path}")
        relative_anchor = self.anchorize(path=relative_path, relative=True)
        self._log_.debug(lambda: f"Page Linking: Relative Anchor = {relative_anchor}")
        relative_endpoint = self.endpointize(path=relative_path, relative=True)
        self._log_.debug(lambda: f"Page Linking: Relative Endpoint = {relative_endpoint}")
        intermediate_alias = inspect_file("/", builder=PurePosixPath)
        _, intermediate_parent = self.locate(endpoint=self.endpointize(path=intermediate_alias, relative=True))
        for part in relative_path.parts[1:-1]:
            intermediate_path = inspect_file(part, header=True, builder=PurePosixPath)
            intermediate_alias /= intermediate_path.name
            self._log_.debug(lambda: f"Page Linking: Intermediate Path = {intermediate_alias}")
            intermediate_anchor = self.anchorize(path=intermediate_alias, relative=True)
            self._log_.debug(lambda: f"Page Linking: Intermediate Anchor = {intermediate_anchor}")
            intermediate_endpoint = self.endpointize(path=intermediate_alias, relative=True)
            self._log_.debug(lambda: f"Page Linking: Intermediate Endpoint = {intermediate_endpoint}")
            _, intermediate_page = self.locate(endpoint=intermediate_endpoint)
            if not intermediate_page:
                intermediate_page = PageAPI(
                    app=self,
                    path=inspect_path(intermediate_alias),
                    description="Resource Not Indexed",
                    add_backward_parent=True,
                    add_backward_children=False,
                    add_current_parent=False,
                    add_current_children=False,
                    add_forward_parent=False,
                    add_forward_children=False
                )
                self._log_.debug(lambda: f"Page Linking: Created Intermediate Page = {intermediate_endpoint}")
            intermediate_page.anchor = intermediate_anchor
            intermediate_page.endpoint = intermediate_endpoint
            intermediate_page._init_()
            self.index(endpoint=intermediate_page.endpoint, page=intermediate_page)
            self._log_.debug(lambda: f"Page Linking: Linked Intermediate Page = {intermediate_endpoint}")
            intermediate_page.attach(parent=intermediate_parent)
            intermediate_parent = intermediate_page
        page.anchor = relative_anchor
        page.endpoint = relative_endpoint
        _, existing = self.locate(endpoint=relative_endpoint)
        if existing:
            page.merge(existing)
            self._log_.debug(lambda: f"Page Linking: Merged Relative Page = {relative_endpoint}")
        else:
            self.index(endpoint=page.endpoint, page=page)
            self._log_.info(lambda: f"Page Linking: Linked {page}")
        page.attach(parent=intermediate_parent)
        page._init_()

    @clientside_callback(
        Input(GLOBAL_ROUTING_STORAGE_ID, "data")
    )
    def _global_async_routing_location_callback_(self):
        return self.asset(path="Callbacks/Routing.js", url=False)

    @serverside_callback(
        Output(GLOBAL_LOCATION_ID, "pathname"),
        Output(GLOBAL_LOCATION_STORAGE_ID, "data"),
        Output(GLOBAL_DESCRIPTION_ID, "children"),
        Output(GLOBAL_NAVIGATION_ID, "children"),
        Output(GLOBAL_SIDEBAR_ID, "children"),
        Output(GLOBAL_CONTENT_ID, "children"),
        Output(GLOBAL_ENTER_ASYNC_ID, "data"),
        Output(GLOBAL_REENTER_ASYNC_ID, "data"),
        Output(GLOBAL_ROUTE_ASYNC_ID, "data"),
        Output(GLOBAL_LEAVE_ASYNC_ID, "data"),
        Input(GLOBAL_LOCATION_ID, "pathname"),
        State(GLOBAL_LOCATION_STORAGE_ID, "data"),
        State(GLOBAL_ENTER_ASYNC_ID, "data"),
        State(GLOBAL_REENTER_ASYNC_ID, "data"),
        State(GLOBAL_ROUTE_ASYNC_ID, "data"),
        State(GLOBAL_LEAVE_ASYNC_ID, "data"),
        on_init=InjectionType.Hidden
    )
    def _global_async_update_location_callback_(self, path: str, location: dict, enter: dict, reenter: dict, route: dict, leave: dict):
        self._log_.debug(lambda: f"Update Location Callback: Received Path = {path}")
        anchor = self.anchorize(path=path, relative=False)
        self._log_.debug(lambda: f"Update Location Callback: Parsed Anchor = {anchor}")
        endpoint = self.endpointize(path=path, relative=False)
        self._log_.debug(lambda: f"Update Location Callback: Parsed Endpoint = {endpoint}")
        location = LocationAPI(**location)
        enter = TriggerAPI(**enter)
        reenter = TriggerAPI(**reenter)
        route = TriggerAPI(**route)
        leave = TriggerAPI(**leave)
        if location.current() == endpoint:
            self._log_.debug(lambda: "Update Location Callback: Current Page Detected")
            enter = dash.no_update
            reenter = reenter.trigger().dict()
            route = route.trigger().dict()
            leave = dash.no_update
        elif location.backward(step=False) == endpoint:
            self._log_.debug(lambda: "Update Location Callback: Backward Page Detected")
            location.backward(step=True)
            enter = enter.trigger().dict()
            reenter = dash.no_update
            route = route.trigger().dict()
            leave = leave.trigger().dict()
        elif location.forward(step=False) == endpoint:
            self._log_.debug(lambda: "Update Location Callback: Forward Page Detected")
            location.forward(step=True)
            enter = enter.trigger().dict()
            reenter = dash.no_update
            route = route.trigger().dict()
            leave = leave.trigger().dict()
        else:
            self._log_.debug(lambda: "Update Location Callback: New Page Detected")
            location.register(path=endpoint)
            enter = enter.trigger().dict()
            reenter = dash.no_update
            route = route.trigger().dict()
            leave = leave.trigger().dict()
        redirect, page = self.redirect(endpoint=endpoint)
        anchor = self.anchorize(path=redirect, relative=False)
        self._log_.debug(lambda: f"Update Location Callback: Normalized Anchor")
        if page:
            description = dash.no_update if (self._description_ or not page.description) else page.description
            self._log_.debug(lambda: f"Update Location Callback: Updated Description")
            navigation = page._navigation_ if page._navigation_ else dash.no_update
            self._log_.debug(lambda: f"Update Location Callback: Updated Navigation")
            sidebar = page._sidebar_
            self._log_.debug(lambda: f"Update Location Callback: Updated Sidebar")
            content = page._content_
            self._log_.debug(lambda: f"Update Location Callback: Updated Content")
        else:
            description = dash.no_update
            self._log_.debug(lambda: f"Update Location Callback: Did not Update Description")
            navigation = dash.no_update
            self._log_.debug(lambda: f"Update Location Callback: Did not Update Navigation")
            sidebar = self.GLOBAL_NOT_FOUND_LAYOUT
            self._log_.debug(lambda: f"Update Location Callback: Updated Sidebar")
            content = self.GLOBAL_NOT_FOUND_LAYOUT
            self._log_.debug(lambda: f"Update Location Callback: Updated Content")
        return anchor, location.dict(), description, navigation, sidebar, content, enter, reenter, route, leave

    @serverside_callback(
        Output(GLOBAL_LOCATION_ID, "pathname"),
        Output(GLOBAL_LOCATION_STORAGE_ID, "data"),
        Input(GLOBAL_BACKWARD_BUTTON_ID, "n_clicks"),
        State(GLOBAL_LOCATION_STORAGE_ID, "data"),
        on_click=InjectionType.Hidden
    )
    def _global_async_backward_location_callback_(self, _, location: dict):
        location = LocationAPI(**location)
        path = location.backward(step=True)
        if not path:
            self._log_.debug(lambda: "Backward Location Callback: No Backward Path Available")
            raise PreventUpdate
        self._log_.debug(lambda: f"Backward Location Callback: Navigating to {path}")
        return path, location.dict()

    @clientside_callback(
        Input(GLOBAL_REFRESH_BUTTON_ID, "n_clicks"),
        Input(GLOBAL_REFRESH_ASYNC_ID, "data")
    )
    def _global_async_refresh_location_callback_(self):
        return self.asset(path="Callbacks/Refresh.js", url=False)

    @serverside_callback(
        Output(GLOBAL_LOCATION_ID, "pathname"),
        Output(GLOBAL_LOCATION_STORAGE_ID, "data"),
        Input(GLOBAL_FORWARD_BUTTON_ID, "n_clicks"),
        State(GLOBAL_LOCATION_STORAGE_ID, "data"),
        on_click=InjectionType.Hidden
    )
    def _global_async_forward_location_callback_(self, _, location: dict):
        location = LocationAPI(**location)
        path = location.forward(step=True)
        if not path:
            self._log_.debug(lambda: "Forward Location Callback: No Forward Path Available")
            raise PreventUpdate
        self._log_.debug(lambda: f"Forward Location Callback: Navigating to {path}")
        return path, location.dict()

    @clientside_callback(
        Output(GLOBAL_SIDEBAR_COLLAPSE_ID, "is_open"),
        Input(GLOBAL_SIDEBAR_BUTTON_ID, "n_clicks"),
        State(GLOBAL_SIDEBAR_COLLAPSE_ID, "is_open"),
        on_click=InjectionType.Hidden
    )
    def _global_async_sidebar_button_callback_(self):
        return self.asset(path="Callbacks/Collapse.js", url=False)

    @clientside_callback(
        Output(GLOBAL_CONTACTS_COLLAPSE_ID, "is_open"),
        Output(GLOBAL_CONTACTS_ARROW_ID, "className"),
        Input(GLOBAL_CONTACTS_BUTTON_ID, "n_clicks"),
        State(GLOBAL_CONTACTS_COLLAPSE_ID, "is_open"),
        State(GLOBAL_CONTACTS_ARROW_ID, "className"),
        on_click=InjectionType.Hidden
    )
    def _global_async_contacts_button_callback_(self):
        return self.asset(path="Callbacks/Collapse.js", url=False)

    @clientside_callback(
        Input(GLOBAL_EMAIL_STORAGE_ID, "data")
    )
    def _global_async_email_client_callback_(self):
        return self.asset(path="Callbacks/Email.js", url=False)

    @clientside_callback(
        Input(GLOBAL_IMPORT_UPLOAD_ID, "contents"),
        State(GLOBAL_IMPORT_UPLOAD_ID, "filename")
    )
    def _global_async_import_snapshot_callback_(self):
        return self.asset(path="Callbacks/Import.js", url=False)

    @clientside_callback(
        Output(GLOBAL_EXPORT_DOWNLOAD_ID, "data"),
        Input(GLOBAL_EXPORT_ID, "n_clicks"),
        State(GLOBAL_LOCATION_ID, "pathname"),
        State({"app": dash.ALL, "page": dash.ALL, "type": dash.ALL, "name": dash.ALL, "portable": "data"}, "data"),
        State({"app": dash.ALL, "page": dash.ALL, "type": dash.ALL, "name": dash.ALL, "portable": "value"}, "value"),
        State({"app": dash.ALL, "page": dash.ALL, "type": dash.ALL, "name": dash.ALL, "portable": "input"}, "input"),
        State({"app": dash.ALL, "page": dash.ALL, "type": dash.ALL, "name": dash.ALL, "portable": "filter"}, "filter"),
        State({"app": dash.ALL, "page": dash.ALL, "type": dash.ALL, "name": dash.ALL, "portable": "date"}, "date"),
        State({"app": dash.ALL, "page": dash.ALL, "type": dash.ALL, "name": dash.ALL, "portable": "checked"}, "checked"),
        State({"app": dash.ALL, "page": dash.ALL, "type": dash.ALL, "name": dash.ALL, "portable": "start_date"}, "start_date"),
        State({"app": dash.ALL, "page": dash.ALL, "type": dash.ALL, "name": dash.ALL, "portable": "end_date"}, "end_date"),
        State({"app": dash.ALL, "page": dash.ALL, "type": dash.ALL, "name": dash.ALL, "portable": "options"}, "options"),
        State({"app": dash.ALL, "page": dash.ALL, "type": dash.ALL, "name": dash.ALL, "portable": "disabled"}, "disabled"),
        State({"app": dash.ALL, "page": dash.ALL, "type": dash.ALL, "name": dash.ALL, "portable": "is_open"}, "is_open"),
        State({"app": dash.ALL, "page": dash.ALL, "type": dash.ALL, "name": dash.ALL, "portable": "active_tab"}, "active_tab")
    )
    def _global_async_export_snapshot_callback_(self):
        return self.asset(path="Callbacks/Export.js", url=False)

    @clientside_callback(
        Output(GLOBAL_MEMORY_STORAGE_ID, "data"),
        on_clean_memory=InjectionType.Hidden
    )
    def _global_async_clean_memory_callback_(self):
        return self.asset(path="Callbacks/Clear.js", url=False)

    @clientside_callback(
        Output(GLOBAL_SESSION_STORAGE_ID, "data"),
        on_clean_session=InjectionType.Hidden
    )
    def _global_async_clean_session_callback_(self):
        return self.asset(path="Callbacks/Clear.js", url=False)

    @clientside_callback(
        Output(GLOBAL_LOCAL_STORAGE_ID, "data"),
        on_clean_local=InjectionType.Hidden
    )
    def _global_async_clean_local_callback_(self):
        return self.asset(path="Callbacks/Clear.js", url=False)

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
        return self.asset(path="Callbacks/Reset.js", url=False)

    @serverside_callback(
        Output(GLOBAL_REFRESH_ASYNC_ID, "data"),
        State(GLOBAL_REFRESH_ASYNC_ID, "data"),
        State(GLOBAL_LOCATION_ID, "pathname"),
        on_clean_reset=InjectionType.Hidden
    )
    def _global_sync_clean_reset_callback_(self, refresh: dict, pathname: str):
        self._injector_.on_clean_memory.reset()
        self._injector_.on_clean_session.reset()
        self._injector_.on_clean_local.reset()
        self._log_.debug(lambda: f"Clean Reset Sync: Waiting")
        endpoint = self.endpointize(path=pathname, relative=False)
        target_memory = self._injector_.on_clean_memory.count(page=endpoint)
        target_session = self._injector_.on_clean_session.count(page=endpoint)
        target_local = self._injector_.on_clean_local.count(page=endpoint)
        attempts = 0
        while attempts < 1000:
            if (self._injector_.on_clean_memory.index >= target_memory and
                self._injector_.on_clean_session.index >= target_session and
                self._injector_.on_clean_local.index >= target_local):
                break
            time.sleep(0.01)
            attempts += 1
        self._log_.debug(lambda: f"Clean Reset Sync: Refreshing")
        refresh = TriggerAPI(**refresh)
        return refresh.trigger().dict()

    @serverside_callback(
        Input(GLOBAL_MEMORY_STORAGE_ID, "data")
    )
    def _global_async_update_memory_callback_(self, data):
        self._log_.info(lambda: f"Global Memory Storage: {data if data else 'Empty'}")
        if not data: self._injector_.on_clean_memory.increment()

    @serverside_callback(
        Input(GLOBAL_SESSION_STORAGE_ID, "data")
    )
    def _global_async_update_session_callback_(self, data):
        self._log_.info(lambda: f"Global Session Storage: {data if data else 'Empty'}")
        if not data: self._injector_.on_clean_session.increment()

    @serverside_callback(
        Input(GLOBAL_LOCAL_STORAGE_ID, "data")
    )
    def _global_async_update_local_callback_(self, data):
        self._log_.info(lambda: f"Global Local Storage: {data if data else 'Empty'}")
        if not data: self._injector_.on_clean_local.increment()

    @staticmethod
    def _global_async_stream_callback_(logs: list[Component], elements: list[Component], limit: int):
        if not logs: raise PreventUpdate
        if not elements: return logs[-limit:]
        patch = dash.Patch()
        patch.extend(logs)
        overflow = len(elements) + len(logs) - limit
        for _ in range(overflow): del patch[0]
        return patch

    @clientside_callback(
        Output(GLOBAL_MODAL_ID, "is_open"),
        Input(GLOBAL_MODAL_BUTTON_ID, "n_clicks")
    )
    def _global_async_dismiss_modal_callback_(self):
        return self.asset(path="Callbacks/Dismiss.js", url=False)

    @serverside_callback(
        Output(GLOBAL_NOTIFICATION_ID, "children"),
        Input(GLOBAL_HIGH_FREQUENCY_INTERVAL_ID, "n_intervals"),
        State(GLOBAL_NOTIFICATION_ID, "children")
    )
    def _global_async_notification_stream_callback_(self, _, notifications: list[Component]):
        return self._global_async_stream_callback_(logs=self.notify.stream(), elements=notifications, limit=self._notification_limit_)

    def ids(self) -> None:
        """
        Override this method to register custom Dash IDs.
        """
        pass

    def components(self) -> None:
        """
        Override this method to initialize shared components.
        """
        pass

    def pages(self) -> None:
        """
        Override this method to register pages.
        """
        pass

    def run(self):
        self._log_.info(lambda: f"Starting Server at {self._host_url_}")
        return self.app.run(
            host=self._host_,
            port=self._port_,
            proxy=self._proxy_,
            debug=self._debug_,
            jupyter_mode="external",
            jupyter_server_url=self._domain_url_
        )

    def mount(self):
        app = FastAPI()
        path: str = self._endpoint_
        self._log_.info(lambda: f"Mounting Server at {path}")
        app.mount(path, WSGIMiddleware(self.app.server))
        return app

    def __repr__(self) -> str:
        return repr(f"{self.__class__.__name__} @ {self._host_url_}")