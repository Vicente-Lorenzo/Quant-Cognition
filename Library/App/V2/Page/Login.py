from dash import dcc, html

from Library.App.V2.Component.Component import Component, IconAPI, TextAPI, InputAPI, ButtonAPI
from Library.App.V2.Page.Page import PageAPI

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
                *InputAPI(id=app.GLOBAL_LOGINPAGE_USER_ID, placeholder="Username", type="text", name="username", autocomplete="username", classname="app-login-input").build(),
                *InputAPI(id=app.GLOBAL_LOGINPAGE_PASS_ID, placeholder="Password", type="password", name="password", autocomplete="current-password", submits=0, classname="app-login-input").build(),
                *ButtonAPI(id=app.GLOBAL_LOGINPAGE_SUBMIT_ID, background="primary", clicks=0, type="button", classname="app-login-submit", label=[IconAPI(icon="bi bi-box-arrow-in-right"), TextAPI(text="Sign In")]).build(),
            ], className="app-login-form"),
        ]
        if not app._private_():
            children.append(dcc.Link([html.I(className="bi bi-person-badge"), html.Span("Continue as Guest")], href=app._endpoint_, className="app-login-guest"))
        if app._contact_:
            children.append(html.Div([
                html.Span("Need an account?", className="app-login-hint"),
                *ButtonAPI(id=app.GLOBAL_LOGINPAGE_SIGNUP_ID, background="link", clicks=0, type="button", classname="app-login-signup", label=[IconAPI(icon="bi bi-person-plus"), TextAPI(text="Request Access")]).build(),
            ], className="app-login-signup-row"))
        return html.Div(html.Div(children, className="app-login-card"), className="app-login-page")