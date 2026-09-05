import uuid

import dash
from dash import html
import dash_bootstrap_components as dbc

from Library.App.V2 import FieldAPI, ComponentID, ButtonAPI, ModalAPI, Output, Input, State, InjectionType, RefreshAPI, serverside_callback
from Library.Logging import VerboseLevel
from Library.Scheduler import ManagerAPI
from Library.Utility.Datetime import HORIZON
from Library.Strategy.Strategy import StrategyType
from Library.System.Learning import FitnessType, RewardType
from Library.System.Selection import ElectionMode, SelectionMode
from Library.System.System import SystemType
from Library.Universe.Contract import CommissionType, SpreadType, SwapType

_STRATEGIES_ = [{"label": member.name, "value": member.name} for member in StrategyType]
_FITNESS_ = [{"label": member.name, "value": member.name} for member in FitnessType]
_SELECTION_ = [{"label": member.name, "value": member.name} for member in SelectionMode]
_ELECTION_ = [{"label": member.name, "value": member.name} for member in ElectionMode]
_SYSTEMS_ = [{"label": name, "value": name} for name in (SystemType.Backtesting.name, SystemType.Optimization.name, SystemType.Learning.name)]
_VERBOSE_ = [{"label": member.name, "value": member.name} for member in VerboseLevel]
_RESOLUTION_ = [{"label": name, "value": name} for name in ("Auto", "M1", "H1", "D1")]
_REWARD_ = [{"label": member.name, "value": member.name} for member in RewardType]
_SPREAD_ = [{"label": member.name, "value": member.name} for member in SpreadType]
_COMMISSION_ = [{"label": member.name, "value": member.name} for member in CommissionType]
_SWAP_ = [{"label": member.name, "value": member.name} for member in SwapType]

MARKET = (
    FieldAPI(name="strategy", control="select", group="market", default=StrategyType.Trend.name, options=_STRATEGIES_, help="Trading rules the engine runs"),
    FieldAPI(name="provider", group="market", default="Spotware", help="Broker whose parameter tree and data are used"),
    FieldAPI(name="ticker", group="market", default="EURUSD", help="Security traded during the run"),
    FieldAPI(name="timeframe", group="market", default="Daily", help="Friendly parameter-tree key · Hour or Daily · never H1 or D1"),
    FieldAPI(name="risk_free", label="Risk Free Rate", control="number", group="market", default=0.0, minimum=0, help="Annual risk free rate as a decimal · 0.04 is 4% · used by Alpha and every ratio"),
    FieldAPI(name="benchmark", group="market", help="Optional comparison series rebased alongside the strategy growth"),
    FieldAPI(name="description", control="textarea", group="market", help="Free text stored with the run for later recall"),
    FieldAPI(name="start", group="period", default=HORIZON.strftime("%Y-%m-%d"), help="First timestamp of the simulated period"),
    FieldAPI(name="stop", group="period", default="2030-01-01", help="Last timestamp of the simulated period"),
    FieldAPI(name="account_asset", label="Account Asset", group="account", default="EUR", help="Deposit currency of the simulated account"),
    FieldAPI(name="account_balance", label="Account Balance", control="number", group="account", default=10000.0, minimum=0, help="Opening balance of the simulated account"),
    FieldAPI(name="account_leverage", label="Account Leverage", control="number", group="account", default=30.0, minimum=1, help="Leverage the simulated account trades with"),
    FieldAPI(name="spread_type", label="Spread Type", control="select", group="cost", default=SpreadType.Auto.name, options=_SPREAD_, help="How the spread is priced · Accurate derives it from the tick tape"),
    FieldAPI(name="spread_value", label="Spread Value", control="number", group="cost", help="Fixed spread in points when the type is not Accurate"),
    FieldAPI(name="commission_type", label="Commission Type", control="select", group="cost", default=CommissionType.Auto.name, options=_COMMISSION_, help="How commission is charged · Points matches an IC Markets raw account"),
    FieldAPI(name="commission_value", label="Commission Value", control="number", group="cost", help="Commission in the unit the type selects · 3.5 points is the thesis condition"),
    FieldAPI(name="swap_type", label="Swap Type", control="select", group="cost", default=SwapType.Auto.name, options=_SWAP_, help="How overnight financing is charged · the thesis runs swap free"),
    FieldAPI(name="swap_buy", label="Swap Buy", control="number", group="cost", help="Overnight financing applied to long exposure · 0 is swap free"),
    FieldAPI(name="swap_sell", label="Swap Sell", control="number", group="cost", help="Overnight financing applied to short exposure · 0 is swap free"),
)

BACKTESTING = (
    FieldAPI(name="resolution", control="select", group="resolution", options=_RESOLUTION_, help="Bar resolution the engine steps on · Auto picks the finest available"),
)

OUTPUT = (
    FieldAPI(name="report", control="switch", group="output", default=True, help="Print the result tables to the run log"),
    FieldAPI(name="export", control="switch", group="output", default=True, help="Write the result tables as CSV under the run Output folder"),
    FieldAPI(name="plot", control="switch", group="output", default=True, help="Render the interactive result view under the run Output folder"),
    FieldAPI(name="console", control="select", group="verbosity", default=VerboseLevel.Info.name, options=_VERBOSE_, help="Console verbosity of the run"),
    FieldAPI(name="file", control="select", group="verbosity", default=VerboseLevel.Debug.name, options=_VERBOSE_, help="File verbosity of the run"),
    FieldAPI(name="storage", control="select", group="verbosity", default=VerboseLevel.Warning.name, options=_VERBOSE_, help="Database verbosity of the run · kept only while the run is retained"),
)

LEARNING = (
    FieldAPI(name="selection", control="select", group="objective", default=SelectionMode.Best.name, options=_SELECTION_, help="Which candidate wins inside a fold · Plateau prefers a stable neighborhood"),
    FieldAPI(name="election", control="select", group="objective", default=ElectionMode.Last.name, options=_ELECTION_, help="Which model wins across folds"),
    FieldAPI(name="purge", control="number", group="guard", default=0, minimum=0, help="Days trimmed from the end of each training window"),
    FieldAPI(name="embargo", control="number", group="guard", default=0, minimum=0, help="Days skipped after each validation window"),
    FieldAPI(name="reward", control="select", group="objective", default=RewardType.LogReturn.name, options=_REWARD_, help="Per step reward the agent maximises"),
    FieldAPI(name="episodes", control="number", group="cadence", default=1, minimum=1, help="Passes over the training tape"),
    FieldAPI(name="epochs", control="number", group="cadence", default=1, minimum=1, help="Gradient epochs per pass"),
    FieldAPI(name="train_frequency", label="Train Frequency", control="number", group="steps", default=1, minimum=1, help="Environment steps between gradient updates"),
    FieldAPI(name="gradient_steps", label="Gradient Steps", control="number", group="steps", default=1, minimum=1, help="Gradient updates applied at each training step"),
    FieldAPI(name="training", control="number", group="split", default=0, minimum=0, help="Walk-forward training window in months · 0 uses the whole period"),
    FieldAPI(name="validation", control="number", group="split", default=0, minimum=0, help="Walk-forward validation window in months"),
    FieldAPI(name="testing", control="number", group="split", default=0, minimum=0, help="Held-out testing window in months · the elected model is re-run here"),
    FieldAPI(name="rolling", control="switch", group="mode", default=False, help="Roll the walk-forward window instead of anchoring it"),
    FieldAPI(name="continuous", control="switch", group="mode", default=False, help="Carry the trained agent into the next fold instead of starting fresh"),
    FieldAPI(name="fitness", control="select", group="objective", default=FitnessType.AnnualizedReturn.name, options=_FITNESS_, help="Metric a single run is scored on"),
    FieldAPI(name="patience", control="number", group="cadence", default=0, minimum=0, help="Episodes without improvement before training stops · 0 disables early stopping"),
    FieldAPI(name="activity", control="number", group="gate", default=0, minimum=0, help="Minimum trades a candidate must place to be admissible"),
    FieldAPI(name="balance", control="number", group="gate", default=0, minimum=0, help="Minimum trades on the weaker side before a candidate is admissible"),
    FieldAPI(name="ratio", control="number", group="gate", default=0.0, minimum=0, help="Minimum share of directional time on the weaker side · the two sided gate"),
    FieldAPI(name="mirror", control="switch", group="gate", default=False, help="Train on the mirrored tape as well so the agent sees both directions"),
    FieldAPI(name="mirror_ratio", label="Mirror Ratio", control="number", group="gate", default=0.5, minimum=0, help="Share of episodes drawn from the mirrored tape"),
    FieldAPI(name="final", control="switch", group="mode", default=False, help="Keep the last checkpoint instead of the best scoring one"),
    FieldAPI(name="seed", control="number", group="fleet", help="Fix the starting seed · empty draws one per run"),
    FieldAPI(name="seeds", control="number", group="fleet", default=1, minimum=1, help="Independent seeds trained per fold"),
    FieldAPI(name="workers", control="number", group="fleet", default=1, minimum=1, help="Worker processes training in parallel"),
    FieldAPI(name="threads", control="number", group="fleet", minimum=1, help="Torch threads per worker · 1 is required for bit exact reproducibility"),
)

OPTIMIZATION = (
    FieldAPI(name="training", control="number", group="split", default=0, minimum=0, help="Walk-forward training window in months · 0 uses the whole period"),
    FieldAPI(name="validation", control="number", group="split", default=0, minimum=0, help="Walk-forward validation window in months"),
    FieldAPI(name="testing", control="number", group="split", default=0, minimum=0, help="Held-out testing window in months · the elected candidate is re-run here"),
    FieldAPI(name="fitness", control="select", group="objective", default=FitnessType.AnnualizedReturn.name, options=_FITNESS_, help="Metric a single run is scored on"),
    FieldAPI(name="resolution", control="select", group="resolution", options=_RESOLUTION_, help="Bar resolution the engine steps on · Auto picks the finest available"),
    FieldAPI(name="selection", control="select", group="objective", default=SelectionMode.Best.name, options=_SELECTION_, help="Which candidate wins inside a fold · Plateau prefers a stable neighborhood"),
    FieldAPI(name="election", control="select", group="objective", default=ElectionMode.Frequency.name, options=_ELECTION_, help="Which model wins across folds"),
    FieldAPI(name="purge", control="number", group="guard", default=0, minimum=0, help="Days trimmed from the end of each training window"),
    FieldAPI(name="embargo", control="number", group="guard", default=0, minimum=0, help="Days skipped after each validation window"),
    FieldAPI(name="rolling", control="switch", group="mode", default=False, help="Roll the walk-forward window instead of anchoring it"),
    FieldAPI(name="continuous", control="switch", group="mode", default=False, help="Carry the elected candidate into the next fold and refine around it"),
    FieldAPI(name="workers", control="number", group="fleet", default=1, minimum=1, help="Worker processes sweeping candidates in parallel"),
)

SYSTEM = FieldAPI(
    name="system",
    control="select",
    group="system",
    default=SystemType.Backtesting.name,
    options=_SYSTEMS_,
    help="Which engine to run · the remaining fields that do not apply are ignored"
)

SYSTEMS = {
    SystemType.Backtesting.name: MARKET + BACKTESTING + OUTPUT,
    SystemType.Optimization.name: MARKET + OPTIMIZATION + OUTPUT,
    SystemType.Learning.name: MARKET + LEARNING + OUTPUT,
}

TASKS = {
    SystemType.Backtesting.name: "Research.Backtesting",
    SystemType.Optimization.name: "Research.Optimization",
    SystemType.Learning.name: "Research.Learning",
}

def merge(*groups) -> tuple:
    seen, merged = set(), []
    for group in groups:
        for entry in group:
            if entry.name in seen: continue
            seen.add(entry.name)
            merged.append(entry)
    return tuple(merged)

EVERY = merge((SYSTEM,), MARKET, BACKTESTING, OPTIMIZATION, LEARNING, OUTPUT)

class LaunchAPI:

    LAUNCH_BTN: ComponentID | dict = ComponentID()
    LAUNCH_MODAL_ID: ComponentID | dict = ComponentID()
    LAUNCH_SUBMIT_BTN: ComponentID | dict = ComponentID()
    LAUNCH_DISCARD_BTN: ComponentID | dict = ComponentID()
    LAUNCH_PREVIEW_ID: ComponentID | dict = ComponentID()

    _LAUNCH_: tuple = ()
    _SYSTEM_: str = SystemType.Backtesting.name
    _SYSTEMS_: dict = {}
    _TASKS_: dict = {}
    _TASK_: str = None

    def _launch_ids_(self) -> None:
        self.LAUNCH_BTN = self.register(type="button", name="launch")
        self.LAUNCH_MODAL_ID = self.register(type="modal", name="launch")
        self.LAUNCH_SUBMIT_BTN = self.register(type="button", name="launch-submit")
        self.LAUNCH_DISCARD_BTN = self.register(type="button", name="launch-discard")
        self.LAUNCH_PREVIEW_ID = self.register(type="text", name="launch-preview")
        for entry in self._LAUNCH_: setattr(self, entry.attribute, self.register(type="field", name=entry.name))

    def _manager_api_(self) -> ManagerAPI:
        return ManagerAPI(database="Quant")

    def _launch_button_(self) -> ButtonAPI:
        return ButtonAPI(
            id=self.LAUNCH_BTN,
            label=self._icon_("bi bi-play-fill", f"Run {self._SYSTEM_}", tint="success"),
            background="secondary",
            tooltip=f"Configure and dispatch a {self._SYSTEM_.lower()} run"
        )

    def _block_(self, entry: FieldAPI):
        if entry.switched:
            return html.Div([*entry.build(self), *self._help_(entry.help)], className="app-switch-field")
        caption = [dbc.Label(entry.label), *self._help_(entry.help)]
        return html.Div([html.Div(caption, className="app-field-label"), *entry.build(self)], className="app-field")

    def _form_(self) -> list:
        body, row, current = [], [], None
        for entry in self._LAUNCH_:
            block = self._block_(entry)
            if entry.group and entry.group == current:
                row.append(block)
                continue
            if row: body.append(html.Div(row, className="app-field-row"))
            row, current = ([block], entry.group) if entry.group else ([], None)
            if not entry.group: body.append(block)
        if row: body.append(html.Div(row, className="app-field-row"))
        return body

    def _launch_modal_(self) -> ModalAPI:
        return ModalAPI(id=self.LAUNCH_MODAL_ID, size="lg", centered=True, scrollable=True, open=False,
                        header=[html.Span(f"Run {self._SYSTEM_}", className="modal-title")],
                        body=self._form_() + [html.Div(id=self.LAUNCH_PREVIEW_ID, className="launch-preview")],
                        footer=[*ButtonAPI(id=self.LAUNCH_DISCARD_BTN, label=self._icon_("bi bi-x-lg", "Cancel", tint="danger"), background="secondary", tooltip="Close without launching").build(),
                                *ButtonAPI(id=self.LAUNCH_SUBMIT_BTN, label=self._icon_("bi bi-play-fill", "Run", tint="success"), background="secondary", tooltip="Queue the run with these arguments").build()])

    def _chosen_(self, values) -> str:
        if not self._SYSTEMS_: return self._SYSTEM_
        return dict(zip((entry.name for entry in self._LAUNCH_), values)).get("system") or self._SYSTEM_

    def _command_(self, values) -> str:
        system = self._chosen_(values)
        if not self._SYSTEMS_: return FieldAPI.command(self._LAUNCH_, values, system)
        allowed = {entry.name for entry in self._SYSTEMS_.get(system, ())}
        pairs = [(entry, value) for entry, value in zip(self._LAUNCH_, values) if entry.name in allowed]
        return FieldAPI.command([entry for entry, _ in pairs], [value for _, value in pairs], system)

    def _dispatch_(self, values) -> tuple:
        system = self._chosen_(values)
        task = self._TASKS_.get(system, self._TASK_)
        if not task:
            self.app.notify.error(f"No {system.lower()} task is registered · run Setup Install", header="Not Configured")
            return dash.no_update, dash.no_update
        arguments = self._command_(values)
        try:
            run = self._manager_api_().run_task(task, arguments=arguments)
        except Exception as error:
            self.app.notify.error(str(error), header="Dispatch Failed")
            return dash.no_update, dash.no_update
        if run is None and self._manager_api_().task(task) is None:
            self.app.notify.error(f"Task '{task}' was not found", header="Dispatch Failed")
            return dash.no_update, dash.no_update
        self.app.notify.success(f"{system} queued · {arguments}", header="Dispatched")
        return False, uuid.uuid4().hex

def launch_callbacks(fields: tuple) -> tuple:
    @serverside_callback(Output(LaunchAPI.LAUNCH_MODAL_ID, "is_open"), Input(LaunchAPI.LAUNCH_BTN, "n_clicks"), on_click=InjectionType.Hidden)
    def _open_launch_(self, clicks):
        return True

    @serverside_callback(Output(LaunchAPI.LAUNCH_MODAL_ID, "is_open"), Input(LaunchAPI.LAUNCH_DISCARD_BTN, "n_clicks"), on_click=InjectionType.Hidden)
    def _close_launch_(self, clicks):
        return False

    @serverside_callback(
        Output(LaunchAPI.LAUNCH_MODAL_ID, "is_open"),
        Output(RefreshAPI.RELOAD_STORE_ID, "data"),
        Input(LaunchAPI.LAUNCH_SUBMIT_BTN, "n_clicks"),
        *[State(entry.id, "value") for entry in fields],
        on_click=InjectionType.Hidden,
    )
    def _submit_launch_(self, clicks, *values):
        return self._dispatch_(values)

    return _open_launch_, _close_launch_, _submit_launch_