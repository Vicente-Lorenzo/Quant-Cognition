import uuid

import dash
from dash import html
from dash.exceptions import PreventUpdate

from Library.App.V2 import FieldAPI, RefreshAPI, TableAPI, ComponentID, Output, Input, State, InjectionType, serverside_callback, clientside_callback, ButtonAPI, ModalAPI, ChoiceAPI, SegmentAPI
from Library.Web.Scheduler.Base import SchedulerBaseAPI

class SchedulerEntityAPI(SegmentAPI, SchedulerBaseAPI):

    _CHOICES_ = (
        ChoiceAPI(value="Enabled", label="Enabled", icon="bi bi-check-circle", state="Yes", tooltip="Let the daemon schedule the selected rows"),
        ChoiceAPI(value="Disabled", label="Disabled", icon="bi bi-x-circle", state="No", tooltip="Hold the selected rows back · the daemon skips them"),
    )

    _entity_ = ""
    _FIELDS_: tuple = ()
    _FIELD_: dict = {}

    F_SCHEDULE: ComponentID | dict = ComponentID()
    MODE_STORE_ID: ComponentID | dict = ComponentID()
    MODAL_ID: ComponentID | dict = ComponentID()
    MODAL_TITLE_ID: ComponentID | dict = ComponentID()
    INSERT_BTN: ComponentID | dict = ComponentID()
    EDIT_BTN: ComponentID | dict = ComponentID()
    RUN_BTN: ComponentID | dict = ComponentID()
    ENABLED_SEGMENT: ComponentID | dict = ComponentID()
    DISABLED_SEGMENT: ComponentID | dict = ComponentID()
    DELETE_BTN: ComponentID | dict = ComponentID()
    DISCARD_BTN: ComponentID | dict = ComponentID()
    SAVE_BTN: ComponentID | dict = ComponentID()
    F_UNSCHEDULE: ComponentID | dict = ComponentID()

    def _entity_ids_(self) -> None:
        self.TARGET_STORE_ID = self.register(type="store", name="target")
        self.MODE_STORE_ID = self.register(type="store", name="mode")
        self.MODAL_ID = self.register(type="modal", name=self._entity_)
        self.MODAL_TITLE_ID = self.register(type="text", name=f"{self._entity_}-title")
        self.INSERT_BTN = self.register(type="button", name="insert")
        self.EDIT_BTN = self.register(type="button", name="edit")
        self.RUN_BTN = self.register(type="button", name="run")
        self._segment_ids_()
        self.DELETE_BTN = self.register(type="button", name="delete")
        self.DISCARD_BTN = self.register(type="button", name="discard")
        self.SAVE_BTN = self.register(type="button", name="save")
        self.F_UNSCHEDULE = self.register(type="button", name="unschedule")

    def _lifecycle_buttons_(self, insert: bool = True) -> list:
        entity = self._entity_
        buttons = []
        if insert: buttons.append(ButtonAPI(id=self.INSERT_BTN, label=self._icon_("bi bi-plus-lg", "Insert", tint="primary"), background="secondary", tooltip=f"Create a new {entity}"))
        buttons.append(ButtonAPI(id=self.EDIT_BTN, label=self._icon_("bi bi-pencil", "Edit"), background="secondary", tooltip=f"Edit the selected {entity}"))
        buttons.append(ButtonAPI(id=self.RUN_BTN, label=self._icon_("bi bi-play-fill", "Run", tint="success"), background="secondary", tooltip=f"Run the selected {entity} now"))
        buttons.append(self._segment_())
        buttons.append(ButtonAPI(id=self.DELETE_BTN, label=self._icon_("bi bi-trash3", "Delete", tint="danger"), background="secondary", tooltip=f"Delete the selected {entity} permanently"))
        return buttons

    @classmethod
    def _outputs_(cls, fields) -> list:
        identity = next(entry for entry in fields if entry.identity)
        return [Output(SchedulerEntityAPI.MODAL_ID, "is_open"), Output(SchedulerEntityAPI.MODE_STORE_ID, "data"),
                Output(SchedulerEntityAPI.MODAL_TITLE_ID, "children"), *[Output(entry.id, "value") for entry in fields],
                Output(identity.id, "disabled")]

    @classmethod
    def _states_(cls, fields) -> list:
        return [State(entry.id, "value") for entry in fields]

    def _field_ids_(self) -> None:
        for entry in self._FIELDS_: setattr(self, entry.attribute, self.register(type="field", name=entry.name))

    def _block_(self, entry: FieldAPI):
        if entry.switched: return self._switch_(entry.bind(self), entry.label, entry.initial(self), entry.help)
        control = entry.build(self)
        if entry.suffix: control = [html.Div([*control, *entry.suffix(self)], className=entry.wrapper)]
        return self._field_(entry.label, control, help=entry.help)

    def _form_(self) -> list:
        body, row, current = [], [], None
        for entry in self._FIELDS_:
            if not entry.rendered: continue
            block = self._block_(entry)
            if entry.group and entry.group == current:
                row.append(block)
                continue
            if row: body.append(html.Div(row, className="app-field-row"))
            row, current = ([block], entry.group) if entry.group else ([], None)
            if not entry.group: body.append(block)
        if row: body.append(html.Div(row, className="app-field-row"))
        return body

    def _modal_(self) -> ModalAPI:
        entity = self._entity_.capitalize()
        return ModalAPI(
            id=self.MODAL_ID,
            size="lg",
            centered=True,
            scrollable=True,
            open=False,
            header=[html.Span(f"Insert {entity}", id=self.MODAL_TITLE_ID, className="modal-title")],
            body=self._form_(),
            footer=self._footer_()
        )

    def _blank_(self) -> tuple:
        return (True, {"mode": "create", "uid": None}, f"Insert {self._entity_.capitalize()}",
                *[entry.initial(self) for entry in self._FIELDS_], False)

    def _populate_(self, target) -> tuple:
        uid = target[0] if target and len(target) == 1 else None
        row = self._fetch_(uid) if uid else None
        if row is None:
            self.app.notify.warning(f"Select a single {self._entity_} to edit", header="Selection")
            return (dash.no_update,) * (len(self._FIELDS_) + 4)
        return (True, {"mode": "update", "uid": row.get("UID")}, f"Edit {self._entity_.capitalize()}",
                *[entry.read(row, self) for entry in self._FIELDS_], True)

    def _submit_(self, mode, values) -> tuple:
        entity = self._entity_.capitalize()
        missing = FieldAPI.missing(self._FIELDS_, values)
        if missing:
            self.app.notify.error(f"{missing} {'is' if ' ' not in missing else 'are'} required", header=f"Invalid {entity}")
            return dash.no_update, dash.no_update
        identity = next(value for entry, value in zip(self._FIELDS_, values) if entry.identity)
        update = bool(mode and mode.get("mode") == "update")
        if not update and not identity:
            self.app.notify.error("UID is required", header=f"Invalid {entity}")
            return dash.no_update, dash.no_update
        try:
            fields = FieldAPI.payload(self._FIELDS_, values)
            if update: getattr(self._manager_, f"update_{self._entity_}")(mode["uid"], **fields)
            else: getattr(self._manager_, f"create_{self._entity_}")(UID=identity, Enabled=True, **fields)
        except Exception as error:
            self.app.notify.error(str(error), header="Save Failed")
            return dash.no_update, dash.no_update
        self.app.notify.success(f"{entity} '{mode['uid'] if update else identity}' {'updated' if update else 'created'}", header="Saved")
        return False, uuid.uuid4().hex

    def _cron_(self, link: dict) -> html.Div:
        return html.Div([
            html.A([html.I(className="bi bi-box-arrow-up-right"), html.Span("Validate on crontab.guru")], id=link, href="https://crontab.guru/", target="_blank", className="scheduler-cron"),
            *ButtonAPI(id=self.F_UNSCHEDULE, size="sm", label=self._icon_("bi bi-eraser", "Clear"), background="secondary", tooltip="Remove the schedule · no cron means on-demand only").build(),
        ], className="scheduler-cron-actions")

    def _footer_(self) -> list:
        return [
            *ButtonAPI(id=self.DISCARD_BTN, label=self._icon_("bi bi-x-lg", "Cancel", tint="danger"), background="secondary", tooltip="Close without saving changes").build(),
            *ButtonAPI(id=self.SAVE_BTN, label=self._icon_("bi bi-check-lg", "Apply", tint="success"), background="secondary", tooltip=f"Save the {self._entity_}").build(),
        ]

    @serverside_callback(
        Output(MODAL_ID, "is_open"),
        Input(DISCARD_BTN, "n_clicks"),
        on_click=InjectionType.Hidden,
    )
    def _discard_(self, clicks):
        return False

    @clientside_callback(
        Output(F_SCHEDULE, "value"),
        Input(F_UNSCHEDULE, "n_clicks"),
        on_click=InjectionType.Hidden,
    )
    def _unschedule_(self):
        return self.app.asset("Callbacks/Blank.js", url=False)

    @clientside_callback(
        Output(EDIT_BTN, "disabled"),
        Output(RUN_BTN, "disabled"),
        Output(DELETE_BTN, "disabled"),
        Input(TableAPI.STATE_STORE_ID, "data"),
        on_init=InjectionType.Hidden,
    )
    def _gate_(self):
        return self.app.asset("Callbacks/Gate.js", url=False)

    @serverside_callback(
        Output(RefreshAPI.RELOAD_STORE_ID, "data"),
        Input(RUN_BTN, "n_clicks"),
        State(SchedulerBaseAPI.TARGET_STORE_ID, "data"),
        on_click=InjectionType.Hidden,
    )
    def _run_(self, clicks, target):
        return self._apply_(self._entity_, "run", target)

    @serverside_callback(
        Output(ENABLED_SEGMENT, "disabled"),
        Output(DISABLED_SEGMENT, "disabled"),
        Output(ENABLED_SEGMENT, "active"),
        Output(DISABLED_SEGMENT, "active"),
        Input(TableAPI.STATE_STORE_ID, "data"),
    )
    def _gate_segment_(self, state):
        disabled, active = self._segment_state_(state, "Enabled")
        return (*disabled, *active)

    @serverside_callback(
        Output(RefreshAPI.RELOAD_STORE_ID, "data"),
        Input(ENABLED_SEGMENT, "n_clicks"),
        Input(DISABLED_SEGMENT, "n_clicks"),
        State(SchedulerBaseAPI.TARGET_STORE_ID, "data"),
        on_click=InjectionType.Hidden,
    )
    def _toggle_(self, enabled, disabled, target):
        choice = self._segment_choice_(dash.ctx.triggered_id)
        if choice is None: raise PreventUpdate
        return self._apply_(self._entity_, "enable" if choice == "Enabled" else "disable", target)

    @serverside_callback(
        Output(RefreshAPI.RELOAD_STORE_ID, "data"),
        Input(DELETE_BTN, "n_clicks"),
        State(SchedulerBaseAPI.TARGET_STORE_ID, "data"),
        on_click=InjectionType.Hidden,
    )
    def _delete_(self, clicks, target):
        return self._apply_(self._entity_, "delete", target)