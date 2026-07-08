from dash import html

from Library.App.V2 import FormAPI, ComponentID, Output, Input, serverside_callback, ContainerAPI, TextAPI

class LauncherPageAPI(FormAPI):

    RESULTS_ID: ComponentID | dict = ComponentID()

    def ids(self) -> None:
        self.RESULTS_ID = self.register(type="content", name="results")

    def content(self) -> list:
        return [
            TextAPI(text=self.description or "", classname="page-lead", builder=html.P),
            ContainerAPI(fluid=True, classname="panel", elements=self._configuration_()),
            ContainerAPI(fluid=True, id=self.RESULTS_ID, classname="panel", elements=[TextAPI(text="No runs yet", classname="status-line")]),
        ]

    def _configuration_(self) -> list:
        return [
            TextAPI(text="Configuration", classname="panel-title", builder=html.H5),
            TextAPI(text="Parameter controls coming soon.", builder=html.P),
        ]

    @serverside_callback(
        Output(RESULTS_ID, "children"),
        Input("FORM_ACTION_BUTTON_ID", "n_clicks")
    )
    def _launcher_run_callback_(self, clicks):
        self._log_.info(lambda: f"Launch Operation: Queued ({self._action_}) · Request {clicks}")
        self.app.notify.info(f"{self._action_} · request #{clicks}", header="Queued")
        return TextAPI(text=f"{self._action_} · request #{clicks} accepted", classname="status-line").build()