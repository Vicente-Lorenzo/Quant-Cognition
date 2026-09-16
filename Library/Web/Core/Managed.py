from dash import html

from Library.App.V2 import PageAPI
from Library.Scheduler import ManagerAPI
from Library.Web.Core.Status import StatusAPI

class ManagedPageAPI(StatusAPI, PageAPI):

    _MARKDOWN_COLUMNS_ = {"Status"}

    def __init__(self, *, app, **kwargs) -> None:
        super().__init__(app=app, **kwargs)
        self._manager_ = ManagerAPI(database=app.Database)

    @staticmethod
    def _details_(pairs) -> html.Div:
        rows = []
        for label, value in pairs:
            if value is None or value == "": continue
            display = str(value) if isinstance(value, (str, int, float, bool)) else value
            rows.append(html.Div([html.Span(label, className="scheduler-detail-key"), html.Span(display, className="scheduler-detail-val")], className="scheduler-detail-row"))
        return html.Div(rows, className="scheduler-detail")

    def _markdown_columns_(self) -> set:
        return self._MARKDOWN_COLUMNS_

    def _fingerprint_(self):
        return self._manager_.fingerprint("Scheduler", "Run")