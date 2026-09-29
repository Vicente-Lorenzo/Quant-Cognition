from dash import html

from Library.App.V2 import SectionPageAPI, TableAPI, PointAPI
from Library.Auth import RoleAPI

class DatabasePageAPI(SectionPageAPI):

    def __init__(self, *, app) -> None:
        super().__init__(app=app, path="/database", button="Database", icon="bi bi-database", description="Browse the universe, the tick tape and the mirrored accounts the data services keep current")

class DatabaseTableAPI(TableAPI):

    _NAVIGABLE_ = False

    def _permitted_(self, role: RoleAPI = RoleAPI.Editor) -> bool:
        from flask_login import current_user
        if current_user.grants(role): return True
        self.app.notify.error(f"The {role.name} role is required for this change", header="Forbidden")
        return False

    @staticmethod
    def _card_(label: str, value, tone: str = "") -> html.Div:
        return html.Div([html.Span(label, className="result-card-key"), html.Span(PointAPI.cell(value) if value not in (None, "") else "—", className=f"result-card-val{tone}")], className="result-card")

    @classmethod
    def _group_(cls, title: str, pairs: list, wide: bool = False) -> html.Div | None:
        if not pairs: return None
        return html.Div([html.Div(title, className="result-group-title"), html.Div([cls._card_(label, value) for label, value in pairs], className="result-cards result-cards-wide" if wide else "result-cards")], className="result-group")

    @staticmethod
    def _key_(value) -> str | None:
        return None if value is None else str(value)

    @staticmethod
    def _hint_(text: str) -> html.Span:
        return html.Span(text, className="app-hint")