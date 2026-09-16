from __future__ import annotations

import dash
from enum import Enum
from functools import wraps
from typing_extensions import Self
from abc import ABC, abstractmethod
from typing import Union, TYPE_CHECKING, Callable, Any

if TYPE_CHECKING: from Library.App.V1 import AppAPI, PageAPI
from Library.App.V1.Component import Component
from Library.Utility.Typing import hasattribute, getattribute

class ComponentID:
    def __set_name__(self, owner, name):
        self.name = name
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {getattr(self, 'name', 'Unbound')}>"

class Trigger(ABC):
    def __init__(self, component: Union[str, dict, ComponentID], property: str):
        self.component: Union[str, dict, ComponentID] = component
        self.property: str = property

    @abstractmethod
    def build(self, context: Union[AppAPI, PageAPI]) -> tuple[dict, str]:
        from Library.App.V1.Page import PageAPI
        trigger: str = self.__class__.__name__
        component = self.component.name if isinstance(self.component, ComponentID) else self.component
        if isinstance(component, dict):
            cid = context.identify(**component)
            load: str = "Hardcode Dict"
        elif hasattribute(context, component):
            cid = getattribute(context, component)
            load: str = "Page Attribute" if isinstance(context, PageAPI) else "Global Attribute"
        elif isinstance(context, PageAPI) and hasattribute(context.app, component):
            cid = getattribute(context.app, component)
            load: str = "Global Attribute"
        else:
            cid = component
            load: str = "Hardcode String"
        context._log_.debug(lambda: f"Loaded {load} ({trigger}): {cid} @ {self.property}")
        return cid, self.property

class Output(Trigger):
    def __init__(self, component: Union[str, dict], property: str, allow_duplicate: bool = True):
        super().__init__(component=component, property=property)
        self.allow_duplicate: bool = allow_duplicate
    def build(self, context: Union[AppAPI, PageAPI]) -> dash.Output:
        component, property = super().build(context=context)
        return dash.Output(component_id=component, component_property=property, allow_duplicate=self.allow_duplicate)

class Input(Trigger):
    def __init__(self, component: Union[str, dict], property: str, allow_optional: bool = True):
        super().__init__(component=component, property=property)
        self.allow_optional: bool = allow_optional
    def build(self, context: Union[AppAPI, PageAPI]) -> dash.Input:
        component, property = super().build(context=context)
        return dash.Input(component_id=component, component_property=property, allow_optional=self.allow_optional)

class State(Trigger):
    def __init__(self, component: Union[str, dict], property: str, allow_optional: bool = True):
        super().__init__(component=component, property=property)
        self.allow_optional: bool = allow_optional
    def build(self, context: Union[AppAPI, PageAPI]) -> dash.State:
        component, property = super().build(context=context)
        return dash.State(component_id=component, component_property=property, allow_optional=self.allow_optional)

def flatten(*args) -> list:
    flat = []
    for arg in args:
        if isinstance(arg, (tuple, list)):
            flat.extend(arg)
        else:
            flat.append(arg)
    return flat

def sort(*args):
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
        if isinstance(value, cls):
            return value
        if value is True:
            return default
        return cls.Disabled

def inject_callback_args(mode: InjectionType, injected_args: Union[list, tuple], original_args: Union[list, tuple]):
    i_out, i_in, i_st, i_oth = sort(injected_args)
    o_out, o_in, o_st, o_oth = sort(original_args)
    n_i_in, n_o_in = len(i_in), len(o_in)
    n_i_st, n_o_st = len(i_st), len(o_st)
    if mode == InjectionType.Prepend:
        all_out = i_out + o_out
        all_in = i_in + o_in
        all_st = i_st + o_st
        all_oth = i_oth + o_oth
        s_i_in = slice(0, n_i_in)
        s_o_in = slice(n_i_in, n_i_in + n_o_in)
        st_start = n_i_in + n_o_in
        s_i_st = slice(st_start, st_start + n_i_st)
        s_o_st = slice(st_start + n_i_st, st_start + n_i_st + n_o_st)
    else:
        all_out = o_out + i_out
        all_in = o_in + i_in
        all_st = o_st + i_st
        all_oth = o_oth + i_oth
        s_o_in = slice(0, n_o_in)
        s_i_in = slice(n_o_in, n_o_in + n_i_in)
        st_start = n_o_in + n_i_in
        s_o_st = slice(st_start, st_start + n_o_st)
        s_i_st = slice(st_start + n_o_st, st_start + n_o_st + n_i_st)
    all_args = [*all_out, *all_in, *all_st, *all_oth]
    schema = {
        "s_o_in": s_o_in, "s_i_in": s_i_in,
        "s_o_st": s_o_st, "s_i_st": s_i_st,
        "n_o_out": len(o_out), "n_i_out": len(i_out),
        "n_all_out": len(all_out)
    }
    return all_args, schema

def inject_serverside_callback(
        mode: InjectionType,
        injected_func: Union[Callable, None],
        injected_args: Union[tuple, list],
        original_func: Callable,
        original_args: Union[tuple, list]):
    all_args, schema = inject_callback_args(mode, injected_args, original_args)
    @wraps(original_func)
    def wrapped(*args, **kwargs):
        original_inputs = args[schema["s_o_in"]]
        original_states = args[schema["s_o_st"]]
        injected_inputs = args[schema["s_i_in"]]
        injected_states = args[schema["s_i_st"]]
        injected_outputs = None
        if injected_func and mode != InjectionType.Disabled:
            payload = {
                "injected_inputs": list(injected_inputs),
                "injected_states": list(injected_states),
                "original_inputs": list(original_inputs),
                "original_states": list(original_states)
            }
            injected_outputs = injected_func(payload)
        original_outputs = original_func(*original_inputs, *original_states, **kwargs)
        n_o_out = schema["n_o_out"]
        o_res_list = [original_outputs] if n_o_out == 1 else list(original_outputs) if n_o_out > 1 else []
        if n_o_out > 1 and not isinstance(original_outputs, (list, tuple)):
            raise ValueError(f"Expected {n_o_out} outputs from original function.")
        i_res_list = []
        n_i_out = schema["n_i_out"]
        if n_i_out > 0:
            if injected_outputs is None: i_res_list = [dash.no_update] * n_i_out
            elif n_i_out == 1: i_res_list = [injected_outputs]
            else:
                if not isinstance(injected_outputs, (list, tuple)): raise ValueError(f"Expected {n_i_out} outputs from injected function.")
                i_res_list = list(injected_outputs)
        final_list = i_res_list + o_res_list if mode == InjectionType.Prepend else o_res_list + i_res_list
        n_all_out = schema["n_all_out"]
        if n_all_out == 0: return None
        if n_all_out == 1: return final_list[0]
        return tuple(final_list)
    return wrapped, all_args

def inject_clientside_callback(
        mode: InjectionType,
        injected_func: Union[str, None],
        injected_args: Union[tuple, list],
        original_js: str,
        original_args: Union[tuple, list]):
    all_args, schema = inject_callback_args(mode, injected_args, original_args)
    handler_src = "null" if (injected_func is None or mode == InjectionType.Disabled) else f"({injected_func})"
    no_update = "window.dash_clientside.no_update"
    s_o_in, s_i_in = schema["s_o_in"], schema["s_i_in"]
    s_o_st, s_i_st = schema["s_o_st"], schema["s_i_st"]
    js_concat = "iResList.concat(oResList)" if mode == InjectionType.Prepend else "oResList.concat(iResList)"
    wrapped_js = f"""
    function() {{
        const originalFn = {original_js};
        const injectedFn = {handler_src};
        const args = Array.from(arguments);
        const originalInputs = args.slice({s_o_in.start}, {s_o_in.stop});
        const injectedInputs = args.slice({s_i_in.start}, {s_i_in.stop});
        const originalStates = args.slice({s_o_st.start}, {s_o_st.stop});
        const injectedStates = args.slice({s_i_st.start}, {s_i_st.stop});
        let injectedOutputs = null;
        if (injectedFn) {{
            const payload = {{
                injected_inputs: injectedInputs,
                injected_states: injectedStates,
                original_inputs: originalInputs,
                original_states: originalStates
            }};
            injectedOutputs = injectedFn(payload);
            if (injectedOutputs === {no_update}) return {no_update};
        }}
        const originalOutputs = originalFn(...originalInputs, ...originalStates);
        const oResList = ({schema["n_o_out"]} > 1) ? originalOutputs : (({schema["n_o_out"]} === 1) ? [originalOutputs] : []);
        const iResList = ({schema["n_i_out"]} > 0) ? (Array.isArray(injectedOutputs) ? injectedOutputs : [injectedOutputs ?? {no_update}]) : [];
        const finalList = {js_concat};
        if ({schema["n_all_out"]} <= 1) return finalList.length > 0 ? finalList[0] : undefined;
        return finalList;
    }}
    """
    return wrapped_js, all_args

def callback(
        *args,
        js: bool,
        on_init: Union[bool, InjectionType],
        on_click: Union[bool, InjectionType],
        on_enter: Union[bool, InjectionType],
        on_reenter: Union[bool, InjectionType],
        on_route: Union[bool, InjectionType],
        on_leave: Union[bool, InjectionType],
        on_clean_memory: Union[bool, InjectionType],
        on_clean_session: Union[bool, InjectionType],
        on_clean_local: Union[bool, InjectionType],
        on_clean_reset: Union[bool, InjectionType],
        loading: Union[bool, InjectionType],
        loading_content: Union[bool, InjectionType],
        loading_sidebar: Union[bool, InjectionType],
        email: Union[bool, InjectionType],
        running: list[tuple],
        progress: Union[Component, list[Component]],
        cancel: list[Component],
        interval: int,
        progress_default: Any,
        **kwargs):
    kwargs["prevent_initial_call"] = (
        InjectionType.coerce(on_init) is InjectionType.Disabled and
        InjectionType.coerce(on_enter) is InjectionType.Disabled and
        InjectionType.coerce(on_reenter) is InjectionType.Disabled and
        InjectionType.coerce(on_route) is InjectionType.Disabled and
        InjectionType.coerce(on_leave) is InjectionType.Disabled
    )
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
        func.loading = loading
        func.loading_content = loading_content
        func.loading_sidebar = loading_sidebar
        func.running = running
        func.progress = progress
        func.cancel = cancel
        func.email = email
        func.interval = interval
        func.progress_default = progress_default
        func.args = flatten(*sort(args))
        return func
    return decorator

def clientside_callback(
        *args,
        on_init: Union[bool, InjectionType] = InjectionType.Disabled,
        on_click: Union[bool, InjectionType] = InjectionType.Disabled,
        on_enter: Union[bool, InjectionType] = InjectionType.Disabled,
        on_reenter: Union[bool, InjectionType] = InjectionType.Disabled,
        on_route: Union[bool, InjectionType] = InjectionType.Disabled,
        on_leave: Union[bool, InjectionType] = InjectionType.Disabled,
        on_clean_memory: Union[bool, InjectionType] = InjectionType.Disabled,
        on_clean_session: Union[bool, InjectionType] = InjectionType.Disabled,
        on_clean_local: Union[bool, InjectionType] = InjectionType.Disabled,
        on_clean_reset: Union[bool, InjectionType] = InjectionType.Disabled,
        loading: Union[bool, InjectionType] = InjectionType.Disabled,
        loading_content: Union[bool, InjectionType] = InjectionType.Disabled,
        loading_sidebar: Union[bool, InjectionType] = InjectionType.Disabled,
        email: Union[bool, InjectionType] = InjectionType.Disabled,
        running: list[tuple] = None,
        progress: Union[list[Component], Component] = None,
        cancel: list[Component] = None,
        interval: int = None,
        progress_default: Any = None,
        **kwargs):
    return callback(
        *args,
        js=True,
        on_init=on_init,
        on_click=on_click,
        on_enter=on_enter,
        on_reenter=on_reenter,
        on_route=on_route,
        on_leave=on_leave,
        on_clean_memory=on_clean_memory,
        on_clean_session=on_clean_session,
        on_clean_local=on_clean_local,
        on_clean_reset=on_clean_reset,
        loading=loading,
        loading_content=loading_content,
        loading_sidebar=loading_sidebar,
        email=email,
        running=running,
        progress=progress,
        cancel=cancel,
        interval=interval,
        progress_default=progress_default,
        **kwargs
    )

def serverside_callback(
        *args,
        on_init: Union[bool, InjectionType] = InjectionType.Disabled,
        on_click: Union[bool, InjectionType] = InjectionType.Disabled,
        on_enter: Union[bool, InjectionType] = InjectionType.Disabled,
        on_reenter: Union[bool, InjectionType] = InjectionType.Disabled,
        on_route: Union[bool, InjectionType] = InjectionType.Disabled,
        on_leave: Union[bool, InjectionType] = InjectionType.Disabled,
        on_clean_memory: Union[bool, InjectionType] = InjectionType.Disabled,
        on_clean_session: Union[bool, InjectionType] = InjectionType.Disabled,
        on_clean_local: Union[bool, InjectionType] = InjectionType.Disabled,
        on_clean_reset: Union[bool, InjectionType] = InjectionType.Disabled,
        loading: Union[bool, InjectionType] = InjectionType.Disabled,
        loading_content: Union[bool, InjectionType] = InjectionType.Disabled,
        loading_sidebar: Union[bool, InjectionType] = InjectionType.Disabled,
        email: Union[bool, InjectionType] = InjectionType.Disabled,
        background: bool = False,
        memoize: bool = False,
        manager: str = None,
        running: list[tuple] = None,
        progress: Union[list[Component], Component] = None,
        cancel: list[Component] = None,
        interval: int = None,
        progress_default: Any = None,
        **kwargs):
    return callback(
        *args,
        js=False,
        on_init=on_init,
        on_click=on_click,
        on_enter=on_enter,
        on_reenter=on_reenter,
        on_route=on_route,
        on_leave=on_leave,
        on_clean_memory=on_clean_memory,
        on_clean_session=on_clean_session,
        on_clean_local=on_clean_local,
        on_clean_reset=on_clean_reset,
        loading=loading,
        loading_content=loading_content,
        loading_sidebar=loading_sidebar,
        email=email,
        background=background,
        memoize=memoize,
        manager=manager,
        running=running,
        progress=progress,
        cancel=cancel,
        interval=interval,
        progress_default=progress_default,
        **kwargs
    )