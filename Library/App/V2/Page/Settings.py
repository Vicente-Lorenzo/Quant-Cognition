from dash import dcc, html
import dash_bootstrap_components as dbc

from Library.App.V2.Core.Identity import GlobalAPI
from Library.App.V2.Core.Callback import ComponentID, Output, Input, State, InjectionType, clientside_callback
from Library.App.V2.Component.Component import ButtonAPI, ContainerAPI, IconAPI, TextAPI
from Library.App.V2.Page.Page import PageAPI

class SettingsPageAPI(PageAPI):

    SETTINGS_TABS_ID: ComponentID | dict = ComponentID()
    SETTINGS_MEMORY_EDITOR_ID: ComponentID | dict = ComponentID()
    SETTINGS_SESSION_EDITOR_ID: ComponentID | dict = ComponentID()
    SETTINGS_LOCAL_EDITOR_ID: ComponentID | dict = ComponentID()
    SETTINGS_MEMORY_SAVE_ID: ComponentID | dict = ComponentID()
    SETTINGS_SESSION_SAVE_ID: ComponentID | dict = ComponentID()
    SETTINGS_LOCAL_SAVE_ID: ComponentID | dict = ComponentID()

    def __init__(self, *, app) -> None:
        super().__init__(app=app, path="/settings", button="Settings", icon="bi bi-gear", description="Manage appearance and session preferences")

    def ids(self) -> None:
        self.SETTINGS_TABS_ID = self.register(type="tabs", name="settings")
        self.SETTINGS_MEMORY_EDITOR_ID = self.register(type="textarea", name="memory_editor", portable="value")
        self.SETTINGS_SESSION_EDITOR_ID = self.register(type="textarea", name="session_editor", portable="value")
        self.SETTINGS_LOCAL_EDITOR_ID = self.register(type="textarea", name="local_editor", portable="value")
        self.SETTINGS_MEMORY_SAVE_ID = self.register(type="button", name="memory_save")
        self.SETTINGS_SESSION_SAVE_ID = self.register(type="button", name="session_save")
        self.SETTINGS_LOCAL_SAVE_ID = self.register(type="button", name="local_save")

    def content(self) -> list:
        return [
            html.Div(dbc.Tabs([
                dbc.Tab(self._appearance_().build(), label="Appearance", tab_id="appearance"),
                dbc.Tab(self._security_().build(), label="Security", tab_id="security"),
                dbc.Tab(self._session_().build(), label="Session", tab_id="session"),
            ], id=self.SETTINGS_TABS_ID, active_tab="appearance"), className="settings-tabs"),
        ]

    def _appearance_(self) -> ContainerAPI:
        theme = ButtonAPI(id=self.app.GLOBAL_SETTINGS_THEME_ID, background="secondary", classname="settings-control", label=[IconAPI(id=self.app.GLOBAL_SETTINGS_THEME_ICON_ID, icon="bi bi-circle-half"), TextAPI(id=self.app.GLOBAL_SETTINGS_THEME_LABEL_ID, text="System")])
        return ContainerAPI(fluid=True, id="appearance", classname="panel settings-panel", elements=[
            TextAPI(text="Appearance", classname="panel-title", builder=html.H5),
            TextAPI(text="Cycle between light · dark · system themes · Your choice is remembered on this device", classname="settings-note", builder=html.P),
            ContainerAPI(fluid=True, classname="settings-row", elements=[TextAPI(text="Theme", classname="settings-label"), theme]),
        ])

    def _security_(self) -> ContainerAPI:
        auth = ButtonAPI(id=self.app.GLOBAL_SETTINGS_AUTH_ID, background="primary", classname="settings-control", label=[IconAPI(id=self.app.GLOBAL_SETTINGS_AUTH_ICON_ID, icon="bi bi-box-arrow-in-right"), TextAPI(id=self.app.GLOBAL_SETTINGS_AUTH_LABEL_ID, text="Sign In")])
        return ContainerAPI(fluid=True, id="security", classname="panel settings-panel", elements=[
            TextAPI(text="Security", classname="panel-title", builder=html.H5),
            TextAPI(text="Sign in to authenticate this session · Your account is shown in the header menu", classname="settings-note", builder=html.P),
            ContainerAPI(fluid=True, classname="settings-row", elements=[TextAPI(text="Account", classname="settings-label"), auth]),
        ])

    def _session_(self) -> ContainerAPI:
        return ContainerAPI(fluid=True, id="session", classname="panel settings-panel", elements=[
            TextAPI(text="Session", classname="panel-title", builder=html.H5),
            TextAPI(text="Inspect · edit · save · or clean the raw JSON held in each browser store", classname="settings-note", builder=html.P),
            self._editor_("Memory", "Cleared as soon as the page reloads — the shortest-lived store", self.SETTINGS_MEMORY_EDITOR_ID, self.SETTINGS_MEMORY_SAVE_ID, self.app.GLOBAL_CLEAN_MEMORY_BUTTON_ID),
            self._editor_("Session", "Kept until this browser tab is closed — survives navigation and reloads", self.SETTINGS_SESSION_EDITOR_ID, self.SETTINGS_SESSION_SAVE_ID, self.app.GLOBAL_CLEAN_SESSION_BUTTON_ID),
            self._editor_("Local", "Persisted on this device across visits until you clean it", self.SETTINGS_LOCAL_EDITOR_ID, self.SETTINGS_LOCAL_SAVE_ID, self.app.GLOBAL_CLEAN_LOCAL_BUTTON_ID),
        ])

    def _editor_(self, name: str, hint: str, editor: dict, save: dict, clean: dict) -> ContainerAPI:
        save_button = ButtonAPI(id=save, background="primary", classname="settings-control", label=[IconAPI(icon="bi bi-save"), TextAPI(text="Save")])
        clean_button = ButtonAPI(id=clean, background="danger", classname="settings-control", label=[IconAPI(icon="bi bi-eraser-fill"), TextAPI(text="Clean")])
        return ContainerAPI(fluid=True, classname="settings-editor", elements=[
            ContainerAPI(fluid=True, classname="settings-row", elements=[TextAPI(text=name, classname="settings-label"), ContainerAPI(fluid=True, classname="settings-controls", elements=[save_button, clean_button])]),
            TextAPI(text=hint, classname="settings-hint", builder=html.P),
            dcc.Textarea(id=editor, className="settings-textarea", spellCheck=False, persistence=False),
        ])

    @clientside_callback(
        Output(SETTINGS_TABS_ID, "active_tab"),
        on_enter=InjectionType.Hidden
    )
    def _settings_async_tab_callback_(self):
        return self.app.asset("Callbacks/Tab.js", url=False)

    @clientside_callback(
        Output(GlobalAPI.GLOBAL_LOCATION_ID, "hash"),
        Input(SETTINGS_TABS_ID, "active_tab"),
    )
    def _settings_async_hash_callback_(self):
        return self.app.asset("Callbacks/Hash.js", url=False)

    @clientside_callback(
        Output(SETTINGS_MEMORY_EDITOR_ID, "value"),
        Output(SETTINGS_SESSION_EDITOR_ID, "value"),
        Output(SETTINGS_LOCAL_EDITOR_ID, "value"),
        Input(GlobalAPI.GLOBAL_MEMORY_STORAGE_ID, "data"),
        Input(GlobalAPI.GLOBAL_SESSION_STORAGE_ID, "data"),
        Input(GlobalAPI.GLOBAL_LOCAL_STORAGE_ID, "data"),
        on_init=InjectionType.Hidden
    )
    def _settings_async_load_callback_(self):
        return self.app.asset("Callbacks/Stringify.js", url=False)

    @clientside_callback(
        Output(GlobalAPI.GLOBAL_MEMORY_STORAGE_ID, "data"),
        Input(SETTINGS_MEMORY_SAVE_ID, "n_clicks"),
        State(SETTINGS_MEMORY_EDITOR_ID, "value"),
        on_click=InjectionType.Hidden
    )
    def _settings_async_save_memory_callback_(self):
        return self.app.asset("Callbacks/Parse.js", url=False)

    @clientside_callback(
        Output(GlobalAPI.GLOBAL_SESSION_STORAGE_ID, "data"),
        Input(SETTINGS_SESSION_SAVE_ID, "n_clicks"),
        State(SETTINGS_SESSION_EDITOR_ID, "value"),
        on_click=InjectionType.Hidden
    )
    def _settings_async_save_session_callback_(self):
        return self.app.asset("Callbacks/Parse.js", url=False)

    @clientside_callback(
        Output(GlobalAPI.GLOBAL_LOCAL_STORAGE_ID, "data"),
        Input(SETTINGS_LOCAL_SAVE_ID, "n_clicks"),
        State(SETTINGS_LOCAL_EDITOR_ID, "value"),
        on_click=InjectionType.Hidden
    )
    def _settings_async_save_local_callback_(self):
        return self.app.asset("Callbacks/Parse.js", url=False)