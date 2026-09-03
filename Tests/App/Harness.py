from dash import html

from Library.App.V2 import AppAPI, PageAPI

class HarnessPageAPI(PageAPI):

    def content(self) -> list:
        return [html.Div("content", className="harness-content")]

class HarnessAppAPI(AppAPI):

    def __init__(self, **kwargs) -> None:
        super().__init__(name="Harness", title="Harness", team="Team", contact="team@harness.test",
                         host="127.0.0.1", port=8099, motto=["Keep going"], auth=None, **kwargs)

    def pages(self) -> None:
        self.link(HarnessPageAPI(app=self, path="/alpha", button="Alpha", icon="bi bi-a-circle"))
        self.link(HarnessPageAPI(app=self, path="/alpha/:uid", button="Alpha Detail", parametric=True))
        self.link(HarnessPageAPI(app=self, path="/beta", button="Beta", icon="bi bi-b-circle"))
        self.link(HarnessPageAPI(app=self, path="/gamma", button="Gamma", redirect="/alpha"))

def build() -> HarnessAppAPI:
    return HarnessAppAPI()