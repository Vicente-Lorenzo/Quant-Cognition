import dash
from dash import html

from Library.App.V2 import FieldAPI, RefreshAPI, TableAPI, TextAPI, ContainerAPI, ComponentID, Output, Input, State, InjectionType, serverside_callback, clientside_callback, modal_callbacks, ButtonAPI, ModalAPI, StorageAPI
from Library.Auth import AccessLevel, AccessAPI
from Library.Credential import CredentialAPI, CredentialHealth, CredentialKind, CredentialManagerAPI, LayoutAPI, SecretAPI
from Library.Utility.Datetime import INSTANT

class CredentialPageAPI(TableAPI):

    _COLUMNS_ = ["Service", "Name", "Kind", "Username", "Secret", "Owner", "View", "Edit", "Access", "Health", "Expires", "Used"]
    _ROW_KEY_ = "UID"
    _SHEET_ = "Credentials"
    _NAVIGABLE_ = False
    _POLL_ = 0

    _FIELDS_ = (
        FieldAPI(name="service", required=True, placeholder="Spotware", help="System the credential belongs to · one row per connection"),
        FieldAPI(name="name", required=True, placeholder="Demo account EUR", help="What distinguishes this credential from the others of the same service"),
        FieldAPI(name="kind", control="select", default=CredentialKind.Password.name, options=FieldAPI.choices(CredentialKind.names()), help="Declares which keys the credential carries and which of them are secret"),
        FieldAPI(name="username", control="textarea", help="One value, or a JSON object for several · always visible"),
        FieldAPI(name="secret", control="textarea", help="One value, or a JSON object for several · never shown here · on edit empty keeps it, a JSON object changes only the keys it names and a null removes one"),
        FieldAPI(name="fields", control="textarea", help="JSON object of accessory values that are not secret"),
        FieldAPI(name="expires", label="Expires At", placeholder="2026-12-31 00:00:00", help="When the secret stops working · empty means it never expires"),
        FieldAPI(name="parent", control="select", default="", help="Optional · inherits the values of another credential, such as one application serving several accounts"),
        FieldAPI(name="owner", default=lambda page: page._actor_(), help="Account that owns the credential and always keeps access · only the owner or an Administrator may hand it over"),
        FieldAPI(name="view", label="View Role", control="select", default="", help="Lowest role that may see this row and use it · Owner only keeps it to you"),
        FieldAPI(name="edit", label="Edit Role", control="select", default="", help="Lowest role that may reveal, change and delete it · never below View"),
    )
    _FIELD_ = FieldAPI.index(_FIELDS_)

    MODAL_ID: ComponentID | dict = ComponentID()
    MODAL_TITLE_ID: ComponentID | dict = ComponentID()
    MODE_STORE_ID: ComponentID | dict = ComponentID()
    SECRET_ID: ComponentID | dict = ComponentID()
    INSERT_BTN: ComponentID | dict = ComponentID()
    EDIT_BTN: ComponentID | dict = ComponentID()
    REVEAL_BTN: ComponentID | dict = ComponentID()
    HIDE_BTN: ComponentID | dict = ComponentID()
    DELETE_BTN: ComponentID | dict = ComponentID()
    DISCARD_BTN: ComponentID | dict = ComponentID()
    SAVE_BTN: ComponentID | dict = ComponentID()

    def __init__(self, *, app) -> None:
        super().__init__(app=app, path="/framework/credential", button="Credentials", icon="bi bi-key", description="Store the secrets every external API needs, with the roles allowed to use and to change each one")
        self._manager_ = CredentialManagerAPI(database=app.Database)

    def ids(self) -> None:
        super().ids()
        self.MODAL_ID = self.register(type="modal", name="credential")
        self.MODAL_TITLE_ID = self.register(type="text", name="credential-title")
        self.MODE_STORE_ID = self.register(type="store", name="mode")
        self.SECRET_ID = self.register(type="div", name="secret")
        self.INSERT_BTN = self.register(type="button", name="insert")
        self.EDIT_BTN = self.register(type="button", name="edit")
        self.REVEAL_BTN = self.register(type="button", name="reveal")
        self.HIDE_BTN = self.register(type="button", name="hide")
        self.DELETE_BTN = self.register(type="button", name="delete")
        self.DISCARD_BTN = self.register(type="button", name="discard")
        self.SAVE_BTN = self.register(type="button", name="save")
        for entry in self._FIELDS_: setattr(self, entry.attribute, self.register(type="field", name=entry.name))

    def _actor_(self) -> str:
        return self.app.actor()

    @staticmethod
    def _roles_() -> list:
        return [{"label": AccessAPI.label(None), "value": ""}] + FieldAPI.choices(AccessAPI.roles())

    @staticmethod
    def _threshold_(value: str) -> str:
        return value or None

    @staticmethod
    def _label_(value) -> str:
        return AccessAPI.label(value)

    @staticmethod
    def _entry_(text: str, name: str, *, mapping: bool = False) -> str | None:
        value = CredentialAPI.entry(text)
        if mapping and value is not None and not isinstance(value, dict): raise ValueError(f"Credential {name}: Failed · Expected a JSON object")
        return CredentialAPI.pack(value)

    @staticmethod
    def _flat_(value: str) -> str:
        decoded = CredentialAPI.unpack(value)
        if decoded is None: return ""
        return decoded if isinstance(decoded, str) else " · ".join(f"{name}: {item}" for name, item in decoded.items())

    def _health_(self, expires) -> str:
        health = self._manager_.health(expires)
        led = {CredentialHealth.Never: "none", CredentialHealth.Healthy: "success", CredentialHealth.Expiring: "approving", CredentialHealth.Expired: "failure"}[health]
        return f'<span class="led-tag"><span class="led led-{led}"></span>{health.name}</span>'

    def _markdown_columns_(self) -> set:
        return {"Health"}

    @staticmethod
    def _stamp_(value) -> str:
        return value.strftime(INSTANT) if hasattr(value, "strftime") else ""

    def _row_(self, row: dict) -> dict:
        return {
            "UID": row.get("UID"),
            "Service": row.get("Service"),
            "Name": row.get("Name"),
            "Kind": row.get("Kind"),
            "Username": self._flat_(row.get("Username")),
            "Secret": self._flat_(row.get("Secret")) or SecretAPI.MASK,
            "Owner": row.get("Owner"),
            "View": self._label_(row.get("ViewRole")),
            "Edit": self._label_(row.get("EditRole")),
            "Access": row.get("Access"),
            "Health": self._health_(row.get("ExpiresAt")),
            "Expires": self._stamp_(row.get("ExpiresAt")),
            "Used": self._stamp_(row.get("UsedAt"))
        }

    def _columns_(self) -> list:
        return self._COLUMNS_

    def _rows_(self) -> list:
        return [self._row_(row) for row in self._manager_.credentials(by=self._actor_())]

    def _actions_(self) -> list:
        return [
            ButtonAPI(id=self.INSERT_BTN, label=self._icon_("bi bi-plus-lg", "Insert", tint="primary"), background="secondary", tooltip="Store a new credential"),
            ButtonAPI(id=self.EDIT_BTN, label=self._icon_("bi bi-pencil", "Edit"), background="secondary", tooltip="Change the selected credential · requires the Edit role it carries"),
            ButtonAPI(id=self.REVEAL_BTN, label=self._icon_("bi bi-eye", "Reveal", tint="warning"), background="secondary", tooltip="Show the secret of the selected credential · requires the Edit role it carries"),
            ButtonAPI(id=self.HIDE_BTN, label=self._icon_("bi bi-eye-slash", "Hide"), background="secondary", tooltip="Hide the revealed secret again"),
            ButtonAPI(id=self.DELETE_BTN, label=self._icon_("bi bi-trash3", "Delete", tint="danger"), background="secondary", tooltip="Delete the selected credential permanently"),
        ]

    def _panel_(self, children=None) -> ContainerAPI:
        return ContainerAPI(fluid=True, classname="panel credential-panel", elements=[
            TextAPI(text="Secret", classname="panel-title", builder=html.H5),
            html.Div(children if children is not None else html.Span(SecretAPI.MASK, className="credential-hidden"), id=self.SECRET_ID, className="credential-secret"),
        ])

    def _form_(self) -> list:
        return [html.Div([html.Label(entry.label, className="app-field-label"), *entry.build(self), html.Small(entry.help, className="app-field-help")], className="app-field") for entry in self._FIELDS_]

    def _modal_(self) -> ModalAPI:
        return ModalAPI(
            id=self.MODAL_ID,
            size="lg",
            centered=True,
            scrollable=True,
            open=False,
            header=[html.Span("Insert Credential", id=self.MODAL_TITLE_ID, className="modal-title")],
            body=self._form_(),
            footer=[
                *ButtonAPI(id=self.DISCARD_BTN, label=self._icon_("bi bi-x-lg", "Cancel", tint="danger"), background="secondary", tooltip="Close without saving changes").build(),
                *ButtonAPI(id=self.SAVE_BTN, label=self._icon_("bi bi-check-lg", "Apply", tint="success"), background="secondary", tooltip="Save the credential").build(),
            ]
        )

    def _extras_(self) -> list:
        return [self._modal_(), StorageAPI(id=self.MODE_STORE_ID, data=None)]

    @serverside_callback(
        Output(_FIELD_["view"].id, "options"),
        Output(_FIELD_["edit"].id, "options"),
        Output(_FIELD_["parent"].id, "options"),
        on_enter=InjectionType.Hidden,
    )
    def _options_(self):
        parents = [{"label": "(none)", "value": ""}] + [{"label": f"{row['Service']} · {row['Name']}", "value": row["UID"]} for row in self._manager_.credentials(by=self._actor_())]
        return self._roles_(), self._roles_(), parents

    _discard_, = modal_callbacks(MODAL_ID, closer=DISCARD_BTN)

    @serverside_callback(
        Output(_FIELD_["username"].id, "placeholder"),
        Output(_FIELD_["secret"].id, "placeholder"),
        Input(_FIELD_["kind"].id, "value"),
    )
    def _template_(self, kind):
        return CredentialAPI.pack(LayoutAPI.template(kind)), CredentialAPI.pack(LayoutAPI.template(kind, secret=True))

    @serverside_callback(
        Output(MODAL_ID, "is_open"),
        Output(MODE_STORE_ID, "data"),
        Output(MODAL_TITLE_ID, "children"),
        *[Output(entry.id, "value") for entry in _FIELDS_],
        Input(INSERT_BTN, "n_clicks"),
        on_click=InjectionType.Hidden,
    )
    def _new_(self, clicks):
        return (True, {"mode": "create", "uid": None}, "Insert Credential", *[entry.initial(self) for entry in self._FIELDS_])

    @serverside_callback(
        Output(MODAL_ID, "is_open"),
        Output(MODE_STORE_ID, "data"),
        Output(MODAL_TITLE_ID, "children"),
        *[Output(entry.id, "value") for entry in _FIELDS_],
        Input(EDIT_BTN, "n_clicks"),
        State(TableAPI.STATE_STORE_ID, "data"),
        on_click=InjectionType.Hidden,
    )
    def _open_(self, clicks, state):
        row = self._single_(state, "edit")
        if row is None: return (dash.no_update,) * (len(self._FIELDS_) + 3)
        values = (row.get("Service"), row.get("Name"), row.get("Kind"), CredentialAPI.unpack(row.get("Username")) or "", "",
                  CredentialAPI.unpack(row.get("Fields")) or "", self._stamp_(row.get("ExpiresAt")), row.get("Parent") or "",
                  row.get("Owner") or "", row.get("ViewRole") or "", row.get("EditRole") or "")
        rendered = [value if isinstance(value, str) else CredentialAPI.pack(value) for value in values]
        return (True, {"mode": "update", "uid": row.get("UID")}, "Edit Credential", *rendered)

    def _single_(self, state, action: str) -> dict | None:
        keys = self.selected(state)
        if len(keys) != 1:
            self.app.notify.warning("Select a single credential first", header="Selection")
            return None
        row = self._manager_.credential(keys[0], by=self._actor_())
        if row is None or (action != "view" and row.get("Access") != AccessLevel.Edit.name):
            self.app.notify.error(f"You may not {action} this credential", header="Forbidden")
            return None
        return row

    @serverside_callback(
        Output(MODAL_ID, "is_open"),
        Output(RefreshAPI.RELOAD_STORE_ID, "data"),
        Input(SAVE_BTN, "n_clicks"),
        State(MODE_STORE_ID, "data"),
        *[State(entry.id, "value") for entry in _FIELDS_],
        on_click=InjectionType.Hidden,
    )
    def _save_(self, clicks, mode, *values):
        service, name, kind, username, secret, fields, expires, parent, owner, view, edit = values
        if not service or not name:
            self.app.notify.error("Service and Name are required", header="Invalid Credential")
            return dash.no_update, dash.no_update
        update = bool(mode and mode.get("mode") == "update")
        try:
            payload = {
                "Service": service.strip(), "Name": name.strip(), "Kind": kind,
                "Username": self._entry_(username, "Username"), "Secret": self._entry_(secret, "Secret"), "Fields": self._entry_(fields, "Fields", mapping=True),
                "ExpiresAt": expires or None, "Parent": parent or None, "Owner": (owner or "").strip() or None,
                "ViewRole": self._threshold_(view), "EditRole": self._threshold_(edit)
            }
            if update: saved = self._manager_.update(mode["uid"], by=self._actor_(), **payload)
            else: saved = self._manager_.store(by=self._actor_(), **payload)
        except (ValueError, PermissionError) as error:
            self.app.notify.error(str(error), header="Refused")
            return dash.no_update, dash.no_update
        if saved is None:
            self.app.notify.error("You may not edit this credential", header="Forbidden")
            return dash.no_update, dash.no_update
        self.app.notify.success(f"Credential '{service} · {name}' {'updated' if update else 'stored'}", header="Saved")
        return False, RefreshAPI.token()

    @serverside_callback(
        Output(RefreshAPI.RELOAD_STORE_ID, "data"),
        Input(DELETE_BTN, "n_clicks"),
        State(TableAPI.STATE_STORE_ID, "data"),
        on_click=InjectionType.Hidden,
    )
    def _delete_(self, clicks, state):
        keys = self._selection_(state, "Select a credential first")
        if not keys: return dash.no_update
        return self._tally_(keys, lambda key: self._manager_.delete(key, by=self._actor_()), "credential(s) deleted", "You may not delete the selected credential")

    @serverside_callback(
        Output(SECRET_ID, "children"),
        Input(REVEAL_BTN, "n_clicks"),
        State(TableAPI.STATE_STORE_ID, "data"),
        on_click=InjectionType.Hidden,
    )
    def _reveal_(self, clicks, state):
        keys = self.selected(state)
        if len(keys) != 1:
            self.app.notify.warning("Select a single credential first", header="Selection")
            return dash.no_update
        values = self._manager_.reveal(keys[0], by=self._actor_())
        if values is None:
            self.app.notify.error("You may not reveal this credential", header="Forbidden")
            return dash.no_update
        if not values: return html.Span("This credential stores no secret", className="credential-hidden")
        return [html.Details([html.Summary(name, className="credential-key"), html.Span(value, className="credential-value")], className="credential-row") for name, value in values.items()]

    @serverside_callback(
        Output(SECRET_ID, "children"),
        Input(HIDE_BTN, "n_clicks"),
        on_click=InjectionType.Hidden,
    )
    def _hide_(self, clicks):
        return html.Span(SecretAPI.MASK, className="credential-hidden")

    @serverside_callback(
        Output(SECRET_ID, "children"),
        Input(TableAPI.STATE_STORE_ID, "data"),
    )
    def _conceal_(self, state):
        return html.Span(SecretAPI.MASK, className="credential-hidden")

    @clientside_callback(
        Output(EDIT_BTN, "disabled"),
        Output(REVEAL_BTN, "disabled"),
        Output(DELETE_BTN, "disabled"),
        Input(TableAPI.STATE_STORE_ID, "data"),
        on_init=InjectionType.Hidden,
    )
    def _gate_(self):
        return self.app.asset("Callbacks/GateAccess.js", url=False)

    def content(self) -> list:
        toolbar, *grid = super().content()
        return [
            TextAPI(text="Credentials", classname="page-title", builder=html.H1),
            TextAPI(text="Every secret the framework uses to reach an external system, with the roles allowed to use it and to change it.", classname="page-lead", builder=html.P),
            toolbar,
            self._panel_(),
            *grid,
        ]