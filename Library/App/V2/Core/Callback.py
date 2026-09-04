from __future__ import annotations

import dash
from enum import Enum
from functools import wraps
from typing_extensions import Self
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Callable

from Library.Utility.Typing import hasattribute, getattribute

if TYPE_CHECKING: from Library.App.V2 import AppAPI, PageAPI, Component

class ComponentID:

    def __set_name__(self, owner, name) -> None:
        self.name = name

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {getattr(self, 'name', 'Unbound')}>"

class Trigger(ABC):

    def __init__(self, component: str | dict | ComponentID, property: str) -> None:
        self.component = component
        self.property = property

    @abstractmethod
    def build(self, context: AppAPI | PageAPI) -> tuple[dict, str]:
        from Library.App.V2.Page.Page import PageAPI
        trigger = self.__class__.__name__
        component = self.component.name if isinstance(self.component, ComponentID) else self.component
        if isinstance(component, dict):
            cid = context.identify(**component)
            load = "Hardcode Dict"
        elif hasattribute(context, component):
            cid = getattribute(context, component)
            load = "Page Attribute" if isinstance(context, PageAPI) else "Global Attribute"
        elif isinstance(context, PageAPI) and hasattribute(context.app, component):
            cid = getattribute(context.app, component)
            load = "Global Attribute"
        else:
            cid = component
            load = "Hardcode String"
        context._log_.debug(lambda: f"Trigger Operation: Resolved ({load}) · {trigger} · {cid} @ {self.property}")
        return cid, self.property

class Output(Trigger):

    def __init__(self, component: str | dict | ComponentID, property: str, allow_duplicate: bool = True) -> None:
        super().__init__(component=component, property=property)
        self.allow_duplicate = allow_duplicate

    def build(self, context: AppAPI | PageAPI) -> dash.Output:
        component, property = super().build(context=context)
        return dash.Output(component_id=component, component_property=property, allow_duplicate=self.allow_duplicate)

class Input(Trigger):

    def __init__(self, component: str | dict | ComponentID, property: str, allow_optional: bool = True) -> None:
        super().__init__(component=component, property=property)
        self.allow_optional = allow_optional

    def build(self, context: AppAPI | PageAPI) -> dash.Input:
        component, property = super().build(context=context)
        return dash.Input(component_id=component, component_property=property, allow_optional=self.allow_optional)

class State(Trigger):

    def __init__(self, component: str | dict | ComponentID, property: str, allow_optional: bool = True) -> None:
        super().__init__(component=component, property=property)
        self.allow_optional = allow_optional

    def build(self, context: AppAPI | PageAPI) -> dash.State:
        component, property = super().build(context=context)
        return dash.State(component_id=component, component_property=property, allow_optional=self.allow_optional)

def flatten(*args) -> list:
    flat = []
    for arg in args:
        if isinstance(arg, (tuple, list)): flat.extend(arg)
        else: flat.append(arg)
    return flat

def sort(*args) -> tuple[list, list, list, list]:
    outputs, inputs, states, others = [], [], [], []
    for arg in flatten(*args):
        if isinstance(arg, (Output, dash.dependencies.Output)): outputs.append(arg)
        elif isinstance(arg, (Input, dash.dependencies.Input)): inputs.append(arg)
        elif isinstance(arg, (State, dash.dependencies.State)): states.append(arg)
        else: others.append(arg)
    return outputs, inputs, states, others

class InjectionType(Enum):

    Disabled = 0
    Hidden = 1
    Prepend = 2
    Append = 3

    @classmethod
    def coerce(cls, value, default: InjectionType = Hidden) -> Self:
        if isinstance(value, cls): return value
        if value is True: return default
        return cls.Disabled

def _layout_(specs: list[dict], original_args: list | tuple) -> tuple[list, dict]:
    o_out, o_in, o_st, o_oth = sort(original_args)
    prepared = []
    for spec in specs:
        io, ii, ist, _ = sort(spec["args"])
        prepared.append({**spec, "io": io, "ii": ii, "is": ist})
    prepend = [spec for spec in prepared if spec["mode"] is InjectionType.Prepend]
    append = [spec for spec in prepared if spec["mode"] is not InjectionType.Prepend]
    inputs = []
    for spec in prepend: spec["in_slice"] = (len(inputs), len(inputs) + len(spec["ii"])); inputs += spec["ii"]
    o_in_slice = (len(inputs), len(inputs) + len(o_in)); inputs += o_in
    for spec in append: spec["in_slice"] = (len(inputs), len(inputs) + len(spec["ii"])); inputs += spec["ii"]
    base, states = len(inputs), []
    for spec in prepend: spec["st_slice"] = (base + len(states), base + len(states) + len(spec["is"])); states += spec["is"]
    o_st_slice = (base + len(states), base + len(states) + len(o_st)); states += o_st
    for spec in append: spec["st_slice"] = (base + len(states), base + len(states) + len(spec["is"])); states += spec["is"]
    outputs = [trigger for spec in prepend for trigger in spec["io"]] + o_out + [trigger for spec in append for trigger in spec["io"]]
    all_args = [*outputs, *inputs, *states, *o_oth]
    plan = {"prepared": prepared, "o_in_slice": o_in_slice, "o_st_slice": o_st_slice, "n_o_out": len(o_out), "n_out": len(outputs)}
    return all_args, plan

def _block_(value: Any, count: int) -> list:
    if value is None: return [dash.no_update] * count
    return [value] if count == 1 else list(value)

def inject_serverside(specs: list[dict], original_func: Callable, original_args: list | tuple) -> tuple[Callable, list]:
    all_args, plan = _layout_(specs, original_args)
    prepared, o_in_slice, o_st_slice = plan["prepared"], plan["o_in_slice"], plan["o_st_slice"]
    n_o_out, n_out = plan["n_o_out"], plan["n_out"]
    @wraps(original_func)
    def wrapped(*args, **kwargs):
        ni, ns = list(args[o_in_slice[0]:o_in_slice[1]]), list(args[o_st_slice[0]:o_st_slice[1]])
        ii = [list(args[spec["in_slice"][0]:spec["in_slice"][1]]) for spec in prepared]
        iss = [list(args[spec["st_slice"][0]:spec["st_slice"][1]]) for spec in prepared]
        pre_out = [spec["pre"]({"injected_inputs": ii[i], "injected_states": iss[i], "original_inputs": ni, "original_states": ns}) if spec["pre"] else None for i, spec in enumerate(prepared)]
        fwd_in = [value for i, spec in enumerate(prepared) if spec["mode"] is InjectionType.Prepend for value in ii[i]] + ni + [value for i, spec in enumerate(prepared) if spec["mode"] is InjectionType.Append for value in ii[i]]
        fwd_st = [value for i, spec in enumerate(prepared) if spec["mode"] is InjectionType.Prepend for value in iss[i]] + ns + [value for i, spec in enumerate(prepared) if spec["mode"] is InjectionType.Append for value in iss[i]]
        original_outputs = original_func(*fwd_in, *fwd_st, **kwargs)
        no = [original_outputs] if n_o_out == 1 else list(original_outputs) if n_o_out > 1 else []
        io = [spec["post"]({"injected_inputs": ii[i], "injected_states": iss[i], "original_inputs": ni, "original_states": ns, "injected_outputs": pre_out[i], "original_outputs": no}) if spec["post"] else pre_out[i] for i, spec in enumerate(prepared)]
        result = [value for i, spec in enumerate(prepared) if spec["mode"] is InjectionType.Prepend for value in _block_(io[i], len(spec["io"]))] + no + [value for i, spec in enumerate(prepared) if spec["mode"] is not InjectionType.Prepend for value in _block_(io[i], len(spec["io"]))]
        if n_out == 0: return None
        return result[0] if n_out == 1 else tuple(result)
    return wrapped, all_args

def inject_clientside(specs: list[dict], original_js: str, original_args: list | tuple) -> tuple[str, list]:
    all_args, plan = _layout_(specs, original_args)
    prepared, n_o_out, n_out = plan["prepared"], plan["n_o_out"], plan["n_out"]
    prepend, append = InjectionType.Prepend.value, InjectionType.Append.value
    entries = ["{inA:%d,inB:%d,stA:%d,stB:%d,nio:%d,mode:%d,pre:%s,post:%s}" % (spec["in_slice"][0], spec["in_slice"][1], spec["st_slice"][0], spec["st_slice"][1], len(spec["io"]), spec["mode"].value, f"({spec['pre_js']})" if spec["pre_js"] else "null", f"({spec['post_js']})" if spec["post_js"] else "null") for spec in prepared]
    abort = "nu" if n_out <= 1 else "[" + ",".join(["nu"] * n_out) + "]"
    wrapped_js = f"""
    function() {{
        var nu = window.dash_clientside.no_update;
        var args = Array.from(arguments);
        var specs = [{",".join(entries)}];
        var original = {original_js};
        var ni = args.slice({plan["o_in_slice"][0]}, {plan["o_in_slice"][1]});
        var ns = args.slice({plan["o_st_slice"][0]}, {plan["o_st_slice"][1]});
        var ii = [], iss = [], preOut = [];
        for (var i = 0; i < specs.length; i++) {{ ii.push(args.slice(specs[i].inA, specs[i].inB)); iss.push(args.slice(specs[i].stA, specs[i].stB)); preOut.push(null); }}
        for (var i = 0; i < specs.length; i++) if (specs[i].pre) {{
            var r = specs[i].pre({{injected_inputs: ii[i], injected_states: iss[i], original_inputs: ni, original_states: ns}});
            if (r === nu) return {abort};
            preOut[i] = r;
        }}
        var fin = [], fst = [];
        for (var i = 0; i < specs.length; i++) if (specs[i].mode === {prepend}) {{ fin = fin.concat(ii[i]); fst = fst.concat(iss[i]); }}
        fin = fin.concat(ni); fst = fst.concat(ns);
        for (var i = 0; i < specs.length; i++) if (specs[i].mode === {append}) {{ fin = fin.concat(ii[i]); fst = fst.concat(iss[i]); }}
        var oo = original.apply(null, fin.concat(fst));
        var no = ({n_o_out} > 1) ? oo : (({n_o_out} === 1) ? [oo] : []);
        var io = [];
        for (var i = 0; i < specs.length; i++) io.push(specs[i].post ? specs[i].post({{injected_inputs: ii[i], injected_states: iss[i], original_inputs: ni, original_states: ns, injected_outputs: preOut[i], original_outputs: no}}) : preOut[i]);
        function block(v, c) {{ if (v === null || v === undefined) {{ var a = []; for (var j = 0; j < c; j++) a.push(nu); return a; }} return Array.isArray(v) ? v : [v]; }}
        var res = [];
        for (var i = 0; i < specs.length; i++) if (specs[i].mode === {prepend}) res = res.concat(block(io[i], specs[i].nio));
        res = res.concat(no);
        for (var i = 0; i < specs.length; i++) if (specs[i].mode !== {prepend}) res = res.concat(block(io[i], specs[i].nio));
        if ({n_out} <= 1) return res.length > 0 ? res[0] : undefined;
        return res;
    }}
    """
    return wrapped_js, all_args

def callback(*args,
             js: bool,
             on_init: bool | InjectionType,
             on_click: bool | InjectionType,
             on_enter: bool | InjectionType,
             on_reenter: bool | InjectionType,
             on_route: bool | InjectionType,
             on_leave: bool | InjectionType,
             on_clean_memory: bool | InjectionType,
             on_clean_session: bool | InjectionType,
             on_clean_local: bool | InjectionType,
             on_clean_reset: bool | InjectionType,
             on_loading: bool | InjectionType,
             on_loading_content: bool | InjectionType,
             on_loading_sidebar: bool | InjectionType,
             on_email: bool | InjectionType,
             running: list[tuple],
             progress: Component | list[Component],
             cancel: list[Component],
             interval: int,
             progress_default: Any,
             **kwargs) -> Callable:
    prevent = (
        InjectionType.coerce(on_init) is InjectionType.Disabled and
        InjectionType.coerce(on_enter) is InjectionType.Disabled and
        InjectionType.coerce(on_reenter) is InjectionType.Disabled and
        InjectionType.coerce(on_route) is InjectionType.Disabled and
        InjectionType.coerce(on_leave) is InjectionType.Disabled
    )
    kwargs["prevent_initial_call"] = True if prevent else "initial_duplicate"
    def decorator(func):
        func.callback = True
        func.js = js
        func.kwargs = kwargs
        func.on_init = on_init
        func.on_click = on_click
        func.on_enter = on_enter
        func.on_reenter = on_reenter
        func.on_route = on_route
        func.on_leave = on_leave
        func.on_clean_memory = on_clean_memory
        func.on_clean_session = on_clean_session
        func.on_clean_local = on_clean_local
        func.on_clean_reset = on_clean_reset
        func.on_loading = on_loading
        func.on_loading_content = on_loading_content
        func.on_loading_sidebar = on_loading_sidebar
        func.running = running
        func.progress = progress
        func.cancel = cancel
        func.on_email = on_email
        func.interval = interval
        func.progress_default = progress_default
        func.args = flatten(*sort(args))
        return func
    return decorator

def clientside_callback(*args,
                        on_init: bool | InjectionType = InjectionType.Disabled,
                        on_click: bool | InjectionType = InjectionType.Disabled,
                        on_enter: bool | InjectionType = InjectionType.Disabled,
                        on_reenter: bool | InjectionType = InjectionType.Disabled,
                        on_route: bool | InjectionType = InjectionType.Disabled,
                        on_leave: bool | InjectionType = InjectionType.Disabled,
                        on_clean_memory: bool | InjectionType = InjectionType.Disabled,
                        on_clean_session: bool | InjectionType = InjectionType.Disabled,
                        on_clean_local: bool | InjectionType = InjectionType.Disabled,
                        on_clean_reset: bool | InjectionType = InjectionType.Disabled,
                        on_loading: bool | InjectionType = InjectionType.Disabled,
                        on_loading_content: bool | InjectionType = InjectionType.Disabled,
                        on_loading_sidebar: bool | InjectionType = InjectionType.Disabled,
                        on_email: bool | InjectionType = InjectionType.Disabled,
                        running: list[tuple] = None,
                        progress: Component | list[Component] = None,
                        cancel: list[Component] = None,
                        interval: int = None,
                        progress_default: Any = None,
                        **kwargs) -> Callable:
    return callback(*args, js=True, on_init=on_init, on_click=on_click, on_enter=on_enter, on_reenter=on_reenter, on_route=on_route, on_leave=on_leave, on_clean_memory=on_clean_memory, on_clean_session=on_clean_session, on_clean_local=on_clean_local, on_clean_reset=on_clean_reset, on_loading=on_loading, on_loading_content=on_loading_content, on_loading_sidebar=on_loading_sidebar, on_email=on_email, running=running, progress=progress, cancel=cancel, interval=interval, progress_default=progress_default, **kwargs)

def serverside_callback(*args,
                        on_init: bool | InjectionType = InjectionType.Disabled,
                        on_click: bool | InjectionType = InjectionType.Disabled,
                        on_enter: bool | InjectionType = InjectionType.Disabled,
                        on_reenter: bool | InjectionType = InjectionType.Disabled,
                        on_route: bool | InjectionType = InjectionType.Disabled,
                        on_leave: bool | InjectionType = InjectionType.Disabled,
                        on_clean_memory: bool | InjectionType = InjectionType.Disabled,
                        on_clean_session: bool | InjectionType = InjectionType.Disabled,
                        on_clean_local: bool | InjectionType = InjectionType.Disabled,
                        on_clean_reset: bool | InjectionType = InjectionType.Disabled,
                        on_loading: bool | InjectionType = InjectionType.Disabled,
                        on_loading_content: bool | InjectionType = InjectionType.Disabled,
                        on_loading_sidebar: bool | InjectionType = InjectionType.Disabled,
                        on_email: bool | InjectionType = InjectionType.Disabled,
                        background: bool = False,
                        memoize: bool = False,
                        manager: str = None,
                        running: list[tuple] = None,
                        progress: Component | list[Component] = None,
                        cancel: list[Component] = None,
                        interval: int = None,
                        progress_default: Any = None,
                        **kwargs) -> Callable:
    return callback(*args, js=False, on_init=on_init, on_click=on_click, on_enter=on_enter, on_reenter=on_reenter, on_route=on_route, on_leave=on_leave, on_clean_memory=on_clean_memory, on_clean_session=on_clean_session, on_clean_local=on_clean_local, on_clean_reset=on_clean_reset, on_loading=on_loading, on_loading_content=on_loading_content, on_loading_sidebar=on_loading_sidebar, on_email=on_email, background=background, memoize=memoize, manager=manager, running=running, progress=progress, cancel=cancel, interval=interval, progress_default=progress_default, **kwargs)