from dash import dcc, html
import dash_bootstrap_components as dbc

from Library.App.V2.Component import Component
from Library.App.V2.Page import PageAPI

class LoginPageAPI(PageAPI):

    def __init__(self, *, app) -> None:
        super().__init__(app=app, path="/login", description="Sign in to continue", add_backward_parent=False, add_backward_children=False, add_current_parent=False, add_current_children=False, add_forward_parent=False, add_forward_children=False)

    def content(self) -> Component:
        app = self.app
        children = [
            html.Img(src=app.asset("Images/logo.png"), className="app-login-logo"),
            html.H1(app._name_, className="app-login-title"),
            html.P("Enter your credentials to continue", className="app-login-subtitle"),
            html.Form([
                dbc.Input(id=app.GLOBAL_LOGINPAGE_USER_ID, placeholder="Username", type="text", name="username", autoComplete="username", className="app-login-input"),
                dbc.Input(id=app.GLOBAL_LOGINPAGE_PASS_ID, placeholder="Password", type="password", name="password", autoComplete="current-password", n_submit=0, className="app-login-input"),
                dbc.Button([html.I(className="bi bi-box-arrow-in-right"), html.Span("Sign In")], id=app.GLOBAL_LOGINPAGE_SUBMIT_ID, color="primary", n_clicks=0, type="button", className="app-login-submit"),
            ], className="app-login-form"),
        ]
        if not app._private_():
            children.append(dcc.Link([html.I(className="bi bi-person-badge"), html.Span("Continue as Guest")], href=app._endpoint_, className="app-login-guest"))
        if app._contact_:
            children.append(html.Div([
                html.Span("Need an account?", className="app-login-hint"),
                dbc.Button([html.I(className="bi bi-person-plus"), html.Span("Request Access")], id=app.GLOBAL_LOGINPAGE_SIGNUP_ID, color="link", n_clicks=0, type="button", className="app-login-signup"),
            ], className="app-login-signup-row"))
        return html.Div(html.Div(children, className="app-login-card"), className="app-login-page")