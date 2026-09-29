import dash
from dash import html

from Library.App.V2 import FieldAPI, RefreshAPI, TableAPI, TextAPI, ContainerAPI, ComponentID, Output, Input, State, InjectionType, serverside_callback, clientside_callback, modal_callbacks, ButtonAPI, ModalAPI, StorageAPI
from Library.Auth import AccessLevel, AccessAPI
from Library.Credential import CredentialAPI, Validity, CredentialType, VaultAPI, LayoutAPI, SecretAPI
from Library.Utility.Datetime import instant_to_string

class CredentialPageAPI(TableAPI):

    _COLUMNS_ = ["Service", "Name", "Kind", "Identifier", "Secret", "Owner", "View", "Edit", "Access", "Validity", "Expires", "Used"]
    _ROW_KEY_ = "UID"
    _SHEET_ = "Credentials"
    _NAVIGABLE_ = False
    _POLL_ = 0
    _ROLES_ = [{"label": AccessAPI.label(None), "value": ""}] + FieldAPI.choices(AccessAPI.roles())

    _FIELDS_ = (
        FieldAPI(name="service", required=True, placeholder="Spotware", help="System the credential belongs to · one row per connection"),
        FieldAPI(name="name", required=True, placeholder="Demo account EUR", help="What distinguishes this credential from the others of the same service"),
        FieldAPI(name="kind", control="select", default=CredentialType.Password.name, options=FieldAPI.choices(CredentialType.names()), help="Declares which keys the credential carries and which of them are secret"),
        FieldAPI(name="identifier", control="textarea", help="Who or what the credential names · a username, client id, key id or certificate subject · one value, or a JSON object for several · always visible"),
        FieldAPI(name="secret", control="textarea", help="What proves it · a password, token, client secret or private key · one value, or a JSON object for several · never shown here · on edit empty keeps it, a JSON object changes only the keys it names and a null removes one"),
        FieldAPI(name="fields", control="textarea", help="JSON object of accessory values that are not secret"),
        FieldAPI(name="expires", label="Expires At", placeholder="2026-12-31 00:00:00", help="When the secret stops working · empty means it never expires"),
        FieldAPI(name="parent", control="select", default="", options=[{"label": "(none)", "value": ""}], help="Optional · inherits the values of another credential, such as one application serving several accounts"),
        FieldAPI(name="owner", default=lambda page: page._actor_(), help="Account that owns the credential and always keeps access · only the owner or an Administrator may hand it over"),
        FieldAPI(name="view", label="View Role", control="select", default="", options=_ROLES_, help="Lowest role that may see this row and use it · Owner keeps it to you"),
        FieldAPI(name="edit", label="Edit Role", control="select", default="", options=_ROLES_, help="Lowest role that may reveal, change and delete it · never below View"),
    )
    _FIELD_ = FieldAPI.index(_FIELDS_)

    MODAL_ID: ComponentID | dict = ComponentID()
    MODAL_TITLE_ID: ComponentID | dict = ComponentID()
    MODE_STORE_ID: ComponentID | dict = ComponentID()
    SECRET_ID: ComponentID | dict = ComponentID()
    INSERT_BTN: ComponentID | dict = ComponentID()
    EDIT_BTN: ComponentID | dict = ComponentID()
    REVEAL_BTN: ComponentID | dict = ComponentID()
    TEST_BTN: ComponentID | dict = ComponentID()
    HIDE_BTN: ComponentID | dict = ComponentID()
    DELETE_BTN: ComponentID | dict = ComponentID()
    DISCARD_BTN: ComponentID | dict = ComponentID()
    SAVE_BTN: ComponentID | dict = ComponentID()

    def __init__(self, *, app) -> None:
        super().__init__(app=app, path="/framework/credential", button="Credentials", icon="bi bi-key", description="Store the secrets every external API needs, with the roles allowed to use and to change each one")
        self._vault_ = VaultAPI(database=app.Database, testers={"Spotware": self._spotware_})

    def ids(self) -> None:
        super().ids()
        self.MODAL_ID = self.register(type="modal", name="credential")
        self.MODAL_TITLE_ID = self.register(type="text", name="credential-title")
        self.MODE_STORE_ID = self.register(type="store", name="mode")
        self.SECRET_ID = self.register(type="div", name="secret")
        self.INSERT_BTN = self.register(type="button", name="insert")
        self.EDIT_BTN = self.register(type="button", name="edit")
        self.REVEAL_BTN = self.register(type="button", name="reveal")
        self.TEST_BTN = self.register(type="button", name="test")
        self.HIDE_BTN = self.register(type="button", name="hide")
        self.DELETE_BTN = self.register(type="button", name="delete")
        self.DISCARD_BTN = self.register(type="button", name="discard")
        self.SAVE_BTN = self.register(type="button", name="save")
        for entry in self._FIELDS_: setattr(self, entry.attribute, self.register(type="field", name=entry.name))

    @staticmethod
    def _spotware_(values: dict) -> str:
        from Library.Spotware import SpotwareAPI
        return SpotwareAPI.test(values)

    @staticmethod
    def _mask_() -> html.Span:
        return html.Span(SecretAPI.MASK, className="credential-hidden")

    def _actor_(self) -> str:
        return self.app.actor()

    def _validity_(self, expires) -> str:
        validity = self._vault_.validity(expires)
        led = {Validity.Permanent: "none", Validity.Valid: "success", Validity.Expiring: "approving", Validity.Expired: "failure"}[validity]
        return f'<span class="led-tag"><span class="led led-{led}"></span>{validity.name}</span>'

    def _markdown_columns_(self) -> set:
        return {"Validity"}

    def _row_(self, row: dict) -> dict:
        return {
            "UID": row.get("UID"),
            "Service": row.get("Service"),
            "Name": row.get("Name"),
            "Kind": row.get("Kind"),
            "Identifier": CredentialAPI.flat(row.get("Identifier")),
            "Secret": CredentialAPI.flat(row.get("Secret")) or SecretAPI.MASK,
            "Owner": row.get("Owner"),
            "View": AccessAPI.label(row.get("ViewRole")),
            "Edit": AccessAPI.label(row.get("EditRole")),
            "Access": row.get("Access"),
            "Validity": self._validity_(row.get("ExpiresAt")),
            "Expires": instant_to_string(row.get("ExpiresAt")),
            "Used": instant_to_string(row.get("UsedAt"))
        }

    def _columns_(self) -> list:
        return self._COLUMNS_

    def _rows_(self) -> list:
        return [self._row_(row) for row in self._vault_.credentials(by=self._actor_())]

    def _actions_(self) -> list:
        return [
            ButtonAPI(id=self.INSERT_BTN, label=self._icon_("bi bi-plus-lg", "Insert", tint="primary"), background="secondary", tooltip="Store a new credential"),
            ButtonAPI(id=self.EDIT_BTN, label=self._icon_("bi bi-pencil", "Edit"), background="secondary", tooltip="Change the selected credential · requires the Edit role it carries"),
            ButtonAPI(id=self.REVEAL_BTN, label=self._icon_("bi bi-eye", "Reveal", tint="warning"), background="secondary", tooltip="Show the secret of the selected credential · requires the Edit role it carries"),
            ButtonAPI(id=self.TEST_BTN, label=self._icon_("bi bi-plug", "Test"), background="secondary", tooltip="Connect with the selected credential and report what it reaches · requires the View role it carries"),
            ButtonAPI(id=self.HIDE_BTN, label=self._icon_("bi bi-eye-slash", "Hide"), background="secondary", tooltip="Hide the revealed secret again"),
            ButtonAPI(id=self.DELETE_BTN, label=self._icon_("bi bi-trash3", "Delete", tint="danger"), background="secondary", tooltip="Delete the selected credential permanently"),
        ]

    def _panel_(self, children=None) -> ContainerAPI:
        return ContainerAPI(fluid=True, classname="panel credential-panel", elements=[
            TextAPI(text="Secret", classname="panel-title", builder=html.H5),
            html.Div(children if children is not None else self._mask_(), id=self.SECRET_ID, className="credential-secret"),
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
        Output(_FIELD_["parent"].id, "options"),
        on_enter=InjectionType.Hidden,
    )
    def _options_(self):
        return self._FIELD_["parent"].options + [{"label": f"{row['Service']} · {row['Name']}", "value": row["UID"]} for row in self._vault_.credentials(by=self._actor_()) if not row.get("Parent")]

    _discard_, = modal_callbacks(MODAL_ID, closer=DISCARD_BTN)

    @serverside_callback(
        Output(_FIELD_["identifier"].id, "placeholder"),
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
        row = self._editable_(state)
        if row is None: return (dash.no_update,) * (len(self._FIELDS_) + 3)
        values = (
            row.get("Service"),
            row.get("Name"),
            row.get("Kind"),
            CredentialAPI.unpack(row.get("Identifier")) or "",
            "",
            CredentialAPI.unpack(row.get("Fields")) or "",
            instant_to_string(row.get("ExpiresAt")),
            row.get("Parent") or "",
            row.get("Owner") or "",
            row.get("ViewRole") or "",
            row.get("EditRole") or ""
        )
        rendered = [value if isinstance(value, str) else CredentialAPI.pack(value) for value in values]
        return (True, {"mode": "update", "uid": row.get("UID")}, "Edit Credential", *rendered)

    def _sole_(self, state) -> str | None:
        keys = self.selected(state)
        if len(keys) == 1: return keys[0]
        self.app.notify.warning("Select a single credential first", header="Selection")
        return None

    def _editable_(self, state) -> dict | None:
        key = self._sole_(state)
        if key is None: return None
        row = self._vault_.credential(key, by=self._actor_())
        if row is None or row.get("Access") != AccessLevel.Edit.name:
            self.app.notify.error("You may not edit this credential", header="Forbidden")
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
        service, name, kind, identifier, secret, fields, expires, parent, owner, view, edit = values
        if not service or not name:
            self.app.notify.error("Service and Name are required", header="Invalid Credential")
            return dash.no_update, dash.no_update
        update = bool(mode and mode.get("mode") == "update")
        try:
            payload = {
                "Service": service.strip(),
                "Name": name.strip(),
                "Kind": kind,
                "Identifier": CredentialAPI.entry(identifier, "Identifier"),
                "Secret": CredentialAPI.entry(secret, "Secret"),
                "Fields": CredentialAPI.entry(fields, "Fields", mapping=True),
                "ExpiresAt": expires or None,
                "Parent": parent or None,
                "Owner": (owner or "").strip() or None,
                "ViewRole": view or None,
                "EditRole": edit or None
            }
            if update: saved = self._vault_.update(mode["uid"], by=self._actor_(), **payload)
            else: saved = self._vault_.store(by=self._actor_(), **payload)
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
        return self._tally_(keys, lambda key: self._vault_.delete(key, by=self._actor_()), "credential(s) deleted", "You may not delete the selected credential")

    @serverside_callback(
        Output(SECRET_ID, "children"),
        Input(REVEAL_BTN, "n_clicks"),
        State(TableAPI.STATE_STORE_ID, "data"),
        on_click=InjectionType.Hidden,
    )
    def _reveal_(self, clicks, state):
        key = self._sole_(state)
        if key is None: return dash.no_update
        values = self._vault_.reveal(key, by=self._actor_())
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
        return self._mask_()

    @serverside_callback(
        Output(SECRET_ID, "children"),
        Input(TableAPI.STATE_STORE_ID, "data"),
    )
    def _conceal_(self, state):
        return self._mask_()

    @serverside_callback(
        Output(RefreshAPI.RELOAD_STORE_ID, "data"),
        Input(TEST_BTN, "n_clicks"),
        State(TableAPI.STATE_STORE_ID, "data"),
        on_click=InjectionType.Hidden,
    )
    def _test_(self, clicks, state):
        key = self._sole_(state)
        if key is None: return dash.no_update
        try: message = self._vault_.test(key, by=self._actor_())
        except Exception as error:
            self.app.notify.error(str(error), header="Test Failed")
            return dash.no_update
        self.app.notify.success(message, header="Connected")
        return RefreshAPI.token()

    @clientside_callback(
        Output(EDIT_BTN, "disabled"),
        Output(REVEAL_BTN, "disabled"),
        Output(DELETE_BTN, "disabled"),
        Output(TEST_BTN, "disabled"),
        Input(TableAPI.STATE_STORE_ID, "data"),
        on_init=InjectionType.Hidden,
    )
    def _gate_(self):
        return self.app.asset("Callbacks/GateAccess.js", url=False)

    def content(self) -> list:
        toolbar, *grid = super().content()
        return [toolbar, self._panel_(), *grid]