import functools
from abc import ABC
from typing import Any
from dataclasses import dataclass, field, fields

from dash import html, dcc
import dash_bootstrap_components as dbc
from dash.development.base_component import Component

from Library.App.V2.Session import TriggerAPI
from Library.Utility.Typing import MISSING

def prop(name: str | None = None, default: Any = MISSING):
    return field(default=default, metadata={"prop": name})

@dataclass(kw_only=True)
class ComponentAPI(ABC):

    id: dict = MISSING
    basename: str = "component"
    classname: str = MISSING
    typename: str = MISSING
    stylename: str = MISSING
    style: dict = MISSING
    hidden: bool = MISSING
    tooltip: str = MISSING
    placement: str = MISSING
    element: Any = MISSING
    builder: type[Component] = html.Div

    def __post_init__(self):
        self.id = self.id or {}
        self.classname = " ".join(p for p in (self.basename, self.classname, self.typename, self.stylename) if p) or None
        self.style = self.style or {}

    @staticmethod
    @functools.cache
    def _props_(cls) -> tuple:
        return tuple((f.name, f.metadata["prop"] or f.name) for f in fields(cls) if "prop" in f.metadata)

    def arguments(self) -> dict:
        kwargs = {}
        if self.id: kwargs["id"] = self.id
        if self.classname: kwargs["className"] = self.classname
        if self.style or self.hidden is not MISSING:
            style = dict(self.style)
            if self.hidden is not MISSING: style["display"] = "none" if self.hidden else "flex"
            if style: kwargs["style"] = style
        for name, key in self._props_(type(self)):
            value = getattr(self, name)
            if value is not MISSING: kwargs[key] = value
        return kwargs

    @staticmethod
    def flatten(element: Any) -> list[Component]:
        if element is MISSING or element is None: return []
        element = [element] if not isinstance(element, (tuple, list)) else element
        elements = []
        for e in element:
            if isinstance(e, ComponentAPI): elements.extend(e.build())
            else: elements.append(e)
        return elements

    @staticmethod
    def organize(elements: list[Component]) -> tuple[list[Component], list[Component]]:
        other, hidden = [], []
        for c in elements:
            (hidden if isinstance(c, (dcc.Store, dcc.Download)) else other).append(c)
        return other, hidden

    def _tooltip_(self) -> list[Component]:
        if self.tooltip is MISSING or not self.id: return []
        kwargs = {"target": self.id, "delay": {"show": 400, "hide": 100}}
        if self.placement is not MISSING: kwargs["placement"] = self.placement
        return [dbc.Tooltip(self.tooltip, **kwargs)]

    def serialize(self, elements: list[Component] = None, hidden: list[Component] = None) -> list[Component]:
        return [*(elements or []), *(hidden or []), *self._tooltip_()]

    def build(self) -> list[Component]:
        elements = self.flatten(self.element)
        elements, hidden = self.organize(elements)
        component = self.builder(elements, **self.arguments()) if elements else self.builder(**self.arguments())
        return self.serialize([component], hidden)

    def __repr__(self) -> str:
        return repr(self.build())

@dataclass(kw_only=True)
class IconAPI(ComponentAPI):

    classname: str = "icon"
    builder: type[Component] = html.I

    icon: str = MISSING

    def __post_init__(self):
        if self.icon is not MISSING: self.stylename = self.icon
        super().__post_init__()

@dataclass(kw_only=True)
class TextAPI(ComponentAPI):

    classname: str = "text"
    builder: type[Component] = html.Span

    text: str = MISSING

    def __post_init__(self):
        if self.text is not MISSING: self.element = self.text
        super().__post_init__()

@dataclass(kw_only=True)
class LabelAPI(TextAPI):

    classname: str = "label"
    builder: type[Component] = dbc.FormText

@dataclass(kw_only=True)
class MarkdownAPI(TextAPI):

    classname: str = "markdown"
    builder: type[Component] = dcc.Markdown

    allow_html: bool = prop("dangerously_allow_html")
    dedent: bool = prop()

@dataclass(kw_only=True)
class IntervalAPI(ComponentAPI):

    classname: str = "interval"
    builder: type[Component] = dcc.Interval

    interval: int = prop()
    intervals: int = prop("n_intervals")
    disabled: bool = prop()

    def __post_init__(self):
        super().__post_init__()
        self.classname = None

@dataclass(kw_only=True)
class StorageAPI(ComponentAPI):

    classname: str = "store"
    builder: type[Component] = dcc.Store

    data: dict = prop()
    autoclear: bool = prop("clear_data")
    persistence: str = prop("storage_type")

    def __post_init__(self):
        super().__post_init__()
        self.classname = None

@dataclass(kw_only=True)
class DownloadAPI(ComponentAPI):

    classname: str = "download"
    builder: type[Component] = dcc.Download

    def __post_init__(self):
        super().__post_init__()
        self.classname = None

@dataclass(kw_only=True)
class UploadAPI(ComponentAPI):

    classname: str = "upload"
    builder: type[Component] = dcc.Upload

    accept: str = prop()
    multiple: bool = prop()
    disabled: bool = prop()
    minsize: int = prop("min_size")
    maxsize: int = prop("max_size")

@dataclass(kw_only=True)
class InputAPI(ComponentAPI):

    classname: str = "input"
    builder: type[Component] = dbc.Input

    type: str = prop()
    name: str = prop()
    value: Any = prop()
    placeholder: str = prop()
    autocomplete: str = prop("autoComplete")
    submits: int = prop("n_submit")
    min: int | float = prop()
    max: int | float = prop()
    step: int | float = prop()
    debounce: bool | int = prop()
    disabled: bool = prop()

@dataclass(kw_only=True)
class SelectAPI(ComponentAPI):

    classname: str = "select"
    builder: type[Component] = dbc.Select

    options: list = prop()
    value: str = prop()
    placeholder: str = prop()
    disabled: bool = prop()

@dataclass(kw_only=True)
class SwitchAPI(ComponentAPI):

    classname: str = "switch"
    builder: type[Component] = dbc.Switch

    label: str = prop()
    value: bool = prop()
    disabled: bool = prop()

@dataclass(kw_only=True)
class TextareaAPI(ComponentAPI):

    classname: str = "textarea"
    builder: type[Component] = dbc.Textarea

    value: str = prop()
    placeholder: str = prop()
    rows: int = prop()
    disabled: bool = prop()

@dataclass(kw_only=True)
class ButtonAPI(ComponentAPI):

    classname: str = "button"
    builder: type[Component] = dbc.Button

    label: list[Component] = MISSING
    title: str = prop()
    type: str = prop()
    clicks: int = prop("n_clicks")
    value: str = prop()
    active: bool = prop()
    disabled: bool = prop()
    href: str = prop()
    size: str = prop()
    background: str = prop("color")
    external: bool = MISSING
    download: DownloadAPI | dict = MISSING
    upload: UploadAPI | dict = MISSING
    asyncer: StorageAPI | dict = MISSING
    syncer: StorageAPI | dict = MISSING

    def arguments(self) -> dict:
        kwargs = super().arguments()
        if self.external is not MISSING: kwargs.update(external_link=self.external, target="_blank")
        return kwargs

    def build(self) -> list[Component]:
        button = self.builder(self.flatten(self.label), **self.arguments())
        addons = []
        if self.asyncer is not MISSING:
            addons.append(StorageAPI(id=self.asyncer, data=TriggerAPI().dict()) if isinstance(self.asyncer, dict) else self.asyncer)
        if self.syncer is not MISSING:
            addons.append(StorageAPI(id=self.syncer, data=TriggerAPI().dict()) if isinstance(self.syncer, dict) else self.syncer)
        if self.download is not MISSING:
            addons.append(DownloadAPI(id=self.download) if isinstance(self.download, dict) else self.download)
        if self.upload is not MISSING:
            if isinstance(self.upload, dict): button = UploadAPI(id=self.upload, element=button)
            else:
                self.upload.element = button
                button = self.upload
        button, hidden = self.organize(self.flatten([button]))
        return self.serialize(button, [*hidden, *self.flatten(addons)])

@dataclass(kw_only=True)
class ImageAPI(ComponentAPI):

    classname: str = "image"
    builder: type[Component] = html.Img

    src: str = prop()
    alt: str = prop()

@dataclass(kw_only=True)
class IframeAPI(ComponentAPI):

    classname: str = "iframe"
    builder: type[Component] = html.Iframe

    src: str = prop()
    srcdoc: str = prop("srcDoc")

@dataclass(kw_only=True)
class ContainerAPI(ComponentAPI):

    basename: str = "container"

    elements: list[Component] = MISSING
    builder: type[Component] = dbc.Container

    fluid: str | bool = prop()
    invert: bool = MISSING

    def __post_init__(self):
        if isinstance(self.elements, ComponentAPI): self.elements = [self.elements]
        elif not isinstance(self.elements, list): self.elements = []
        if self.invert is not MISSING and self.invert: self.elements = list(reversed(self.elements))
        super().__post_init__()

    def build(self) -> list[Component]:
        elements, hidden = self.organize(self.flatten(self.elements))
        group = self.builder(elements, **self.arguments())
        return self.serialize([group], hidden)

@dataclass(kw_only=True)
class RowContainerAPI(ContainerAPI):

    classname: str = "row"
    builder: type[Component] = dbc.Row

    align: str = prop()
    justify: str = prop()

@dataclass(kw_only=True)
class ColContainerAPI(ContainerAPI):

    classname: str = "col"
    builder: type[Component] = dbc.Col

    align: str = prop()
    width: int | dict = prop()

@dataclass(kw_only=True)
class ButtonContainerAPI(ContainerAPI):

    classname: str = "buttons"
    builder: type[Component] = dbc.ButtonGroup

    vertical: bool = prop()
    size: str = prop()

@dataclass(kw_only=True)
class DropdownAPI(ComponentAPI):

    classname: str = "dropdown"
    builder: type[Component] = dbc.DropdownMenuItem

    header: bool = prop()
    divider: bool = prop()
    active: bool = prop()
    disabled: bool = prop()

@dataclass(kw_only=True)
class DropdownContainerAPI(ContainerAPI):

    classname: str = "dropdowns"

    direction: str = prop()
    disabled: bool = prop()
    align_end: bool = prop()
    in_navbar: bool = prop()
    in_nav: bool = prop("nav")
    in_group: bool = prop("group")
    size: str = prop()
    background: str = prop("color")

    elements: list[DropdownAPI] = MISSING
    builder: type[Component] = dbc.DropdownMenu

@dataclass(kw_only=True)
class PaginatorAPI(ButtonContainerAPI):

    classname: str = "paginator"

    iid: dict = MISSING
    eid: dict = MISSING
    label: list[Component] = MISSING
    href: str = MISSING
    dropdown: DropdownContainerAPI = MISSING
    disabled: bool = MISSING

    def __post_init__(self):
        internal = ButtonAPI(id=self.iid, href=self.href, title="Open Page", external=False, label=self.label, typename="internal", disabled=self.disabled)
        external = ButtonAPI(id=self.eid, href=self.href, title="Open Page (New Tab)", external=True, typename="external", stylename="bi bi-box-arrow-up-right", disabled=self.disabled)
        self.elements = [internal, external, self.dropdown] if self.dropdown is not MISSING else [internal, external]
        super().__post_init__()

@dataclass(kw_only=True)
class NavigatorAPI(ComponentAPI):

    classname: str = "navigator"
    builder: type[Component] = dbc.NavItem

@dataclass(kw_only=True)
class NavigatorContainerAPI(ContainerAPI):

    classname: str = "navigator"

    elements: list[NavigatorAPI] = MISSING
    builder: type[Component] = dbc.Nav

    vertical: str | bool = prop()
    horizontal: str = prop()
    justified: bool = prop()
    fill: bool = prop()
    in_card: bool = prop("card")
    in_navbar: bool = prop("navbar")

@dataclass(kw_only=True)
class LoadingAPI(ComponentAPI):

    classname: str = "loading"
    builder: type[Component] = html.Div

    color: str = "primary"
    type: str = "border"
    size: str = MISSING

    def build(self) -> list[Component]:
        elements, hidden = self.organize(self.flatten(self.element))
        spinner_kwargs: dict[str, Any] = {"spinner_class_name": "spinner"}
        if self.color is not MISSING: spinner_kwargs["color"] = self.color
        if self.type is not MISSING: spinner_kwargs["type"] = self.type
        if self.size is not MISSING: spinner_kwargs["size"] = self.size
        spinner = dbc.Spinner(elements, **spinner_kwargs) if elements else dbc.Spinner(**spinner_kwargs)
        return self.serialize([self.builder(spinner, **self.arguments())], hidden)

@dataclass(kw_only=True)
class NotificationAPI(ComponentAPI):

    classname: str = "notification"
    builder: type[Component] = dbc.Toast

    icon: str = MISSING
    header: str = MISSING
    background: str = MISSING
    duration: int | None = prop()
    dismissable: bool = prop(default=True)
    persistence: bool | str = prop()

    def __post_init__(self):
        if self.background is not MISSING: self.stylename = " ".join(p for p in (self.background, self.stylename) if p)
        super().__post_init__()

    def arguments(self) -> dict:
        kwargs = super().arguments()
        header_elements = []
        if self.icon is not MISSING: header_elements.extend(IconAPI(icon=self.icon).build())
        if self.header is not MISSING: header_elements.extend(TextAPI(text=self.header).build())
        if header_elements: kwargs["header"] = html.Div(header_elements, className="title")
        return kwargs

@dataclass(kw_only=True)
class ModalAPI(ComponentAPI):

    classname: str = "modal"
    builder: type[Component] = dbc.Modal

    header: list[Component] | str = MISSING
    body: list[Component] = MISSING
    footer: list[Component] = MISSING

    size: str = prop()
    fade: bool = prop()
    open: bool = prop("is_open")
    centered: bool = prop()
    keyboard: bool = prop()
    backdrop: bool | str = prop()
    scrollable: bool = prop()
    fullscreen: bool | str = prop()

    def build(self) -> list[Component]:
        elements = []
        if self.header is not MISSING:
            header_elem = [dbc.ModalTitle(self.header)] if isinstance(self.header, str) else self.flatten(self.header)
            elements.append(dbc.ModalHeader(header_elem))
        if self.body is not MISSING: elements.append(dbc.ModalBody(self.flatten(self.body)))
        if self.footer is not MISSING: elements.append(dbc.ModalFooter(self.flatten(self.footer)))
        elements, hidden = self.organize(elements)
        return self.serialize([self.builder(elements, **self.arguments())], hidden)