from dash import html

from Library.App.V2.Component import ButtonAPI, ContainerAPI, IconAPI, TextAPI
from Library.App.V2.Page import PageAPI

class SettingsPageAPI(PageAPI):

    def __init__(self, *, app) -> None:
        super().__init__(app=app, path="/settings", button="Settings", icon="bi bi-gear", description="Manage appearance and session preferences")

    def content(self) -> list:
        return [
            TextAPI(text="Settings", classname="page-title", builder=html.H1),
            TextAPI(text="Manage appearance and session preferences.", classname="page-lead", builder=html.P),
            self._theme_(),
            self._session_(),
        ]

    def _theme_(self) -> ContainerAPI:
        toggle = ButtonAPI(id=self.app.GLOBAL_SETTINGS_THEME_ID, background="secondary", classname="settings-control", label=[IconAPI(icon="bi bi-circle-half"), TextAPI(text="Toggle Theme")])
        return ContainerAPI(fluid=True, id="theme", classname="panel settings-panel", elements=[
            TextAPI(text="Appearance", classname="panel-title", builder=html.H5),
            TextAPI(text="Switch between light and dark themes · Your choice is remembered on this device", classname="settings-note", builder=html.P),
            ContainerAPI(fluid=True, classname="settings-row", elements=[TextAPI(text="Theme", classname="settings-label"), toggle]),
        ])

    def _session_(self) -> ContainerAPI:
        auth = ButtonAPI(id=self.app.GLOBAL_SETTINGS_AUTH_ID, background="primary", classname="settings-control", label=[IconAPI(icon="bi bi-box-arrow-in-right"), TextAPI(text="Sign In · Sign Out")])
        return ContainerAPI(fluid=True, id="session", classname="panel settings-panel", elements=[
            TextAPI(text="Session", classname="panel-title", builder=html.H5),
            TextAPI(text="Sign in to authenticate this session · Your account is shown in the header menu", classname="settings-note", builder=html.P),
            ContainerAPI(fluid=True, classname="settings-row", elements=[TextAPI(text="Account", classname="settings-label"), auth]),
            TextAPI(text="Clear stored Memory · Session · Local data or Reset everything from the footer controls", classname="settings-hint", builder=html.P),
        ])