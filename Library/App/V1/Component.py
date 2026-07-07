from abc import ABC
from typing import Union, Any
from dataclasses import dataclass, field

from dash import html, dcc
import dash_bootstrap_components as dbc
from dash.development.base_component import Component

from Library.App.V1.Session import TriggerAPI

def parse_id(id: dict = None) -> dict:
    return id or {}

def parse_classname(basename: str = None, classname: str = None, typename: str = None, stylename: str = None) -> str:
    basename: str = basename or ""
    classname: str = classname or ""
    typename: str = typename or ""
    stylename: str = stylename or ""
    return f"{basename} {classname} {typename} {stylename}".strip()

def parse_style(basestyle: dict = None, classstyle: dict = None) -> dict:
    return {**(basestyle or {}), **(classstyle or {})}

@dataclass(kw_only=True)
class ComponentAPI(Component, ABC):

    id: Union[dict, None] = field(default_factory=dict)
    basename: Union[str, None] = field(default="component")
    classname: Union[str, None] = field(default_factory=str)
    typename: Union[str, None] = field(default_factory=str)
    stylename: Union[str, None] = field(default_factory=str)
    style: Union[dict, None] = field(default_factory=dict)
    hidden: Union[bool, None] = field(default=None)

    border_color: Union[str, None] = field(default=None)
    border_style: Union[str, None] = field(default=None)
    border_width: Union[str, None] = field(default=None)
    border_radius: Union[str, None] = field(default=None)

    outline_color: Union[str, None] = field(default=None)
    outline_style: Union[str, None] = field(default=None)
    outline_width: Union[str, None] = field(default=None)
    outline_offset: Union[str, None] = field(default=None)

    background: Union[str, None] = field(default=None)
    size: Union[str, None] = field(default=None)

    padding_top: Union[str, None] = field(default=None)
    padding_right: Union[str, None] = field(default=None)
    padding_bottom: Union[str, None] = field(default=None)
    padding_left: Union[str, None] = field(default=None)

    margin_top: Union[str, None] = field(default=None)
    margin_right: Union[str, None] = field(default=None)
    margin_bottom: Union[str, None] = field(default=None)
    margin_left: Union[str, None] = field(default=None)

    element: Union[Component, Any] = field(default=None)
    builder: type[Component] = field(default=html.Div)

    def __post_init__(self):
        self.id = parse_id(id=self.id)
        self.classname = parse_classname(
            basename=self.basename,
            classname=self.classname,
            typename=self.typename,
            stylename=self.stylename
        )
        self.style = parse_style(basestyle=self.style)

    def arguments(self) -> dict:
        kwargs = {}
        if self.id: kwargs.update(id=self.id)
        if self.classname: kwargs.update(className=self.classname)
        classstyle = {}
        if self.hidden is not None: classstyle = self.display(hidden=self.hidden, style=classstyle)
        if self.border_color is not None: classstyle.update(borderColor=self.border_color)
        if self.border_style is not None: classstyle.update(borderStyle=self.border_style)
        if self.border_width is not None: classstyle.update(borderWidth=self.border_width)
        if self.border_radius is not None: classstyle.update(borderRadius=self.border_radius)
        if self.outline_color is not None: classstyle.update(outlineColor=self.outline_color)
        if self.outline_style is not None: classstyle.update(outlineStyle=self.outline_style)
        if self.outline_width is not None: classstyle.update(outlineWidth=self.outline_width)
        if self.outline_offset is not None: classstyle.update(outlineOffset=self.outline_offset)
        if self.padding_top is not None: classstyle.update(paddingTop=self.padding_top)
        if self.padding_right is not None: classstyle.update(paddingRight=self.padding_right)
        if self.padding_bottom is not None: classstyle.update(paddingBottom=self.padding_bottom)
        if self.padding_left is not None: classstyle.update(paddingLeft=self.padding_left)
        if self.margin_top is not None: classstyle.update(marginTop=self.margin_top)
        if self.margin_right is not None: classstyle.update(marginRight=self.margin_right)
        if self.margin_bottom is not None: classstyle.update(marginBottom=self.margin_bottom)
        if self.margin_left is not None: classstyle.update(marginLeft=self.margin_left)
        self.style = parse_style(basestyle=self.style, classstyle=classstyle)
        if self.style: kwargs.update(style=self.style)
        return kwargs

    @staticmethod
    def display(hidden: bool, style: dict = None) -> dict:
        style = style or {}
        if hidden: style.update(display="none")
        else: style.update(display="flex")
        return style

    @staticmethod
    def flatten(element: Union[Component, list]) -> list[Component]:
        element = [element] if not isinstance(element, (tuple, list)) else element
        elements = []
        for e in element:
            if isinstance(e, ComponentAPI):
                elements.extend(e.build())
            else:
                elements.append(e)
        return elements

    @staticmethod
    def organize(elements: list[Component]) -> tuple[list[Component], list[Component]]:
        listing = (dcc.Store, dcc.Download)
        hidden = [c for c in elements if isinstance(c, listing)]
        other = [c for c in elements if not isinstance(c, listing)]
        return other, hidden

    @staticmethod
    def serialize(elements: list[Component] = None, hidden: list[Component] = None) -> list[Component]:
        elements = elements or []
        hidden = hidden or []
        return [*elements, *hidden]

    def build(self) -> list[Component]:
        elements = self.flatten(element=self.element if self.element is not None else [])
        elements, hidden = self.organize(elements=elements)
        component = self.builder(elements, **self.arguments()) if elements else self.builder(**self.arguments())
        return self.serialize(elements=[component], hidden=hidden)

    def __repr__(self) -> str:
        return repr(self.build())

@dataclass(kw_only=True)
class IconAPI(ComponentAPI):

    classname: Union[str, None] = field(default="icon")
    builder: type[Component] = field(default=html.I)

    icon: str = field(default=None)

    def __post_init__(self):
        if self.icon is not None: self.stylename = self.icon
        super().__post_init__()

@dataclass(kw_only=True)
class TextAPI(ComponentAPI):

    classname: Union[str, None] = field(default="text")
    builder: type[Component] = field(default=html.Span)

    text: str = field(default=None)

    font_weight: Union[str, int] = field(default=None)
    font_color: str = field(default=None)
    font_size: str = field(default=None)
    font_family: str = field(default=None)

    def __post_init__(self):
        if self.text is not None: self.element = self.text
        super().__post_init__()

    def arguments(self) -> dict:
        kwargs = super().arguments()
        textstyle = {}
        if self.font_weight is not None: textstyle.update(fontWeight=self.font_weight)
        if self.font_color is not None: textstyle.update(color=self.font_color)
        if self.font_size is not None: textstyle.update(fontSize=self.font_size)
        if self.font_family is not None: textstyle.update(fontFamily=self.font_family)
        self.style = parse_style(basestyle=self.style, classstyle=textstyle)
        kwargs.update(style=self.style)
        return kwargs

@dataclass(kw_only=True)
class LabelAPI(TextAPI):

    classname: Union[str, None] = field(default="label")
    builder: type[Component] = field(default=dbc.FormText)

@dataclass(kw_only=True)
class MarkdownAPI(TextAPI):

    classname: Union[str, None] = field(default="markdown")
    builder: type[Component] = field(default=dcc.Markdown)

    allow_html: bool = field(default=None)
    dedent: bool = field(default=None)

    def arguments(self) -> dict:
        kwargs = super().arguments()
        if self.allow_html is not None: kwargs.update(dangerously_allow_html=self.allow_html)
        if self.dedent is not None: kwargs.update(dedent=self.dedent)
        return kwargs

@dataclass(kw_only=True)
class IntervalAPI(ComponentAPI):

    classname: Union[str, None] = field(default="interval")
    builder: type[Component] = field(default=dcc.Interval)

    interval: int = field(default=None)
    intervals: int = field(default=0)
    disabled: bool = field(default=None)

    def __post_init__(self):
        super().__post_init__()
        self.classname = None

    def arguments(self) -> dict:
        kwargs = super().arguments()
        if self.interval is not None: kwargs.update(interval=self.interval)
        if self.intervals is not None: kwargs.update(n_intervals=self.intervals)
        if self.disabled is not None: kwargs.update(disabled=self.disabled)
        return kwargs

@dataclass(kw_only=True)
class StorageAPI(ComponentAPI):

    classname: Union[str, None] = field(default="store")
    builder: type[Component] = field(default=dcc.Store)

    data: dict = field(default_factory=dict)
    autoclear: bool = field(default=None)
    persistence: str = field(default=None)

    def __post_init__(self):
        super().__post_init__()
        self.classname = None

    def arguments(self) -> dict:
        kwargs = super().arguments()
        if self.data is not None: kwargs.update(data=self.data)
        if self.autoclear is not None: kwargs.update(clear_data=self.autoclear)
        if self.persistence is not None: kwargs.update(storage_type=self.persistence)
        return kwargs

@dataclass(kw_only=True)
class DownloadAPI(ComponentAPI):

    classname: Union[str, None] = field(default="download")
    builder: type[Component] = field(default=dcc.Download)

    def __post_init__(self):
        super().__post_init__()
        self.classname = None

@dataclass(kw_only=True)
class UploadAPI(ComponentAPI):

    classname: Union[str, None] = field(default="upload")
    builder: type[Component] = field(default=dcc.Upload)

    accept: str = field(default=None)
    multiple: bool = field(default=None)
    disabled: bool = field(default=None)
    minsize: int = field(default=None)
    maxsize: int = field(default=None)

    def arguments(self) -> dict:
        kwargs = super().arguments()
        if self.accept is not None: kwargs.update(accept=self.accept)
        if self.multiple is not None: kwargs.update(multiple=self.multiple)
        if self.disabled is not None: kwargs.update(disabled=self.disabled)
        if self.minsize is not None: kwargs.update(min_size=self.minsize)
        if self.maxsize is not None: kwargs.update(max_size=self.maxsize)
        return kwargs

@dataclass(kw_only=True)
class ButtonAPI(ComponentAPI):

    classname: Union[str, None] = field(default="button")

    label: list[Component] = field(default_factory=list)
    title: str = field(default=None)
    clicks: int = field(default=0)
    value: str = field(default=None)
    active: bool = field(default=None)
    disabled: bool = field(default=None)
    href: str = field(default=None)
    external: bool = field(default=None)
    download: Union[DownloadAPI, dict] = field(default=None)
    upload: Union[UploadAPI, dict] = field(default=None)
    asyncer: Union[StorageAPI, dict] = field(default=None)
    syncer: Union[StorageAPI, dict] = field(default=None)

    def arguments(self) -> dict:
        kwargs = super().arguments()
        if self.title is not None: kwargs.update(title=self.title)
        if self.clicks is not None: kwargs.update(n_clicks=self.clicks)
        if self.value is not None: kwargs.update(value=self.value)
        if self.active is not None: kwargs.update(active=self.active)
        if self.disabled is not None: kwargs.update(disabled=self.disabled)
        if self.href is not None: kwargs.update(href=self.href)
        if self.external is not None: kwargs.update(external_link=self.external, target="_blank")
        if self.background is not None: kwargs.update(color=self.background)
        if self.size is not None: kwargs.update(size=self.size)
        return kwargs

    def build(self) -> list[Component]:
        label = self.flatten(element=self.label)
        button = dbc.Button(label, **self.arguments())
        addons = []
        if self.asyncer:
            if isinstance(self.asyncer, dict):
                addons.append(StorageAPI(id=self.asyncer, data=TriggerAPI().dict()))
            else:
                addons.append(self.asyncer)
        if self.syncer:
            if isinstance(self.syncer, dict):
                addons.append(StorageAPI(id=self.syncer, data=TriggerAPI().dict()))
            else:
                addons.append(self.syncer)
        if self.download:
            if isinstance(self.download, dict):
                addons.append(DownloadAPI(id=self.download))
            else:
                addons.append(self.download)
        if self.upload:
            if isinstance(self.upload, dict):
                button = UploadAPI(id=self.upload, element=button)
            else:
                self.upload.element = button
                button = self.upload
        button = self.flatten(element=[button])
        addons = self.flatten(element=addons)
        button, hidden = self.organize(elements=button)
        hidden = [*hidden, *addons]
        return self.serialize(elements=button, hidden=hidden)

@dataclass(kw_only=True)
class ImageAPI(ComponentAPI):

    classname: Union[str, None] = field(default="image")
    builder: type[Component] = field(default=html.Img)

    src: str = field(default=None)
    alt: str = field(default=None)

    def arguments(self) -> dict:
        kwargs = super().arguments()
        if self.src is not None: kwargs.update(src=self.src)
        if self.alt is not None: kwargs.update(alt=self.alt)
        return kwargs

@dataclass(kw_only=True)
class IframeAPI(ComponentAPI):

    classname: Union[str, None] = field(default="iframe")
    builder: type[Component] = field(default=html.Iframe)

    src: str = field(default=None)
    srcdoc: str = field(default=None)

    def arguments(self) -> dict:
        kwargs = super().arguments()
        if self.src is not None: kwargs.update(src=self.src)
        if self.srcdoc is not None: kwargs.update(srcDoc=self.srcdoc)
        return kwargs

@dataclass(kw_only=True)
class ContainerAPI(ComponentAPI):

    basename: str = field(default="container")

    elements: list[Component] = field(default_factory=list)
    builder: type[Component] = field(default=dbc.Container)

    fluid: Union[str, bool] = field(default=None)
    invert: bool = field(default=None)

    def __post_init__(self):
        if isinstance(self.elements, list): self.elements = self.elements
        elif isinstance(self.elements, ComponentAPI): self.elements = [self.elements]
        else: self.elements = []
        self.elements = self.elements if not self.invert else list(reversed(self.elements))
        for element in (e for e in self.elements if isinstance(e, ComponentAPI)):
            if element.border_color is None: element.border_color = "transparent"
            if element.border_style is None: element.border_style = self.border_style
            if element.border_width is None: element.border_width = self.border_width
            if element.border_radius is None: element.border_radius = self.border_radius
            if element.outline_color is None: element.outline_color = "transparent"
            if element.outline_style is None: element.outline_style = self.outline_style
            if element.outline_width is None: element.outline_width = self.outline_width
            if element.outline_offset is None: element.outline_offset = self.outline_offset
            if element.background is None: element.background = self.background
            if element.size is None: element.size = self.size
        super().__post_init__()

    def arguments(self) -> dict:
        kwargs = super().arguments()
        if self.fluid is not None: kwargs.update(fluid=self.fluid)
        return kwargs

    def build(self) -> list[Component]:
        elements = self.flatten(element=self.elements)
        elements, hidden = self.organize(elements=elements)
        group = self.builder(elements, **self.arguments())
        return self.serialize(elements=[group], hidden=hidden)

@dataclass(kw_only=True)
class RowContainerAPI(ContainerAPI):

    classname: Union[str, None] = field(default="row")

    builder: type[Component] = field(default=dbc.Row)

    align: str = field(default=None)
    justify: str = field(default=None)

    def arguments(self) -> dict:
        kwargs = super().arguments()
        if self.align is not None: kwargs.update(align=self.align)
        if self.justify is not None: kwargs.update(justify=self.justify)
        return kwargs

@dataclass(kw_only=True)
class ColContainerAPI(ContainerAPI):

    classname: Union[str, None] = field(default="col")

    builder: type[Component] = field(default=dbc.Col)

    align: str = field(default=None)
    width: Union[int, dict] = field(default=None)

    def arguments(self) -> dict:
        kwargs = super().arguments()
        if self.align is not None: kwargs.update(align=self.align)
        if self.width is not None: kwargs.update(width=self.width)
        return kwargs

@dataclass(kw_only=True)
class ButtonContainerAPI(ContainerAPI):

    classname: Union[str, None] = field(default="buttons")

    builder: type[Component] = field(default=dbc.ButtonGroup)

    vertical: bool = field(default=None)

    def arguments(self) -> dict:
        kwargs = super().arguments()
        if self.vertical is not None: kwargs.update(vertical=self.vertical)
        if self.size is not None: kwargs.update(size=self.size)
        return kwargs

@dataclass(kw_only=True)
class DropdownAPI(ComponentAPI):

    classname: Union[str, None] = field(default="dropdown")
    builder: type[Component] = field(default=dbc.DropdownMenuItem)

    header: bool = field(default=None)
    divider: bool = field(default=None)
    active: bool = field(default=None)
    disabled: bool = field(default=None)

    def arguments(self) -> dict:
        kwargs = super().arguments()
        if self.header is not None: kwargs.update(header=self.header)
        if self.divider is not None: kwargs.update(divider=self.divider)
        if self.active is not None: kwargs.update(active=self.active)
        if self.disabled is not None: kwargs.update(disabled=self.disabled)
        return kwargs

@dataclass(kw_only=True)
class DropdownContainerAPI(ContainerAPI):

    classname: Union[str, None] = field(default="dropdowns")

    direction: str = field(default="down")
    disabled: bool = field(default=None)
    align_end: bool = field(default=None)
    in_navbar: bool = field(default=None)
    in_nav: bool = field(default=None)
    in_group: bool = field(default=None)

    elements: list[DropdownAPI] = field(default_factory=list)
    builder: type[Component] = field(default=dbc.DropdownMenu)

    def arguments(self) -> dict:
        kwargs = super().arguments()
        if self.direction is not None: kwargs.update(direction=self.direction)
        if self.disabled is not None: kwargs.update(disabled=self.disabled)
        if self.align_end is not None: kwargs.update(align_end=self.align_end)
        if self.in_navbar is not None: kwargs.update(in_navbar=self.in_navbar)
        if self.in_nav is not None: kwargs.update(nav=self.in_nav)
        if self.in_group is not None: kwargs.update(group=self.in_group)
        if self.background is not None: kwargs.update(color=self.background)
        if self.size is not None: kwargs.update(size=self.size)
        return kwargs

@dataclass(kw_only=True)
class PaginatorAPI(ButtonContainerAPI):

    classname: Union[str, None] = field(default="paginator")

    vertical: bool = field(default=None)

    iid: dict = field(default_factory=dict)
    eid: dict = field(default_factory=dict)
    label: list[Component] = field(default_factory=list)
    href: str = field(default=None)
    dropdown: DropdownContainerAPI = field(default=None)
    disabled: bool = field(default=None)

    def __post_init__(self):
        internal = ButtonAPI(
            id=self.iid,
            href=self.href,
            title="Open Page",
            external=False,
            label=self.label,
            typename="internal",
            disabled=self.disabled
        )
        external = ButtonAPI(
            id=self.eid,
            href=self.href,
            title="Open Page (New Tab)",
            external=True,
            typename="external",
            stylename="bi bi-box-arrow-up-right",
            disabled=self.disabled
        )
        self.elements = [internal, external, self.dropdown] if self.dropdown is not None else [internal, external]
        super().__post_init__()

@dataclass(kw_only=True)
class NavigatorAPI(ComponentAPI):

    classname: Union[str, None] = field(default="navigator")
    builder: type[Component] = field(default=dbc.NavItem)

@dataclass(kw_only=True)
class NavigatorContainerAPI(ContainerAPI):

    classname: Union[str, None] = field(default="navigator")

    elements: list[NavigatorAPI] = field(default_factory=list)
    builder: type[Component] = field(default=dbc.Nav)

    vertical: Union[str, bool] = field(default=None)
    horizontal: str = field(default=None)
    justified: bool = field(default=None)
    fill: bool = field(default=None)
    in_card: bool = field(default=None)
    in_navbar: bool = field(default=None)

    def arguments(self) -> dict:
        kwargs = super().arguments()
        if self.vertical is not None: kwargs.update(vertical=self.vertical)
        if self.horizontal is not None: kwargs.update(horizontal=self.horizontal)
        if self.justified is not None: kwargs.update(justified=self.justified)
        if self.fill is not None: kwargs.update(fill=self.fill)
        if self.in_card is not None: kwargs.update(card=self.in_card)
        if self.in_navbar is not None: kwargs.update(navbar=self.in_navbar)
        return kwargs

@dataclass(kw_only=True)
class LoadingAPI(ComponentAPI):

    classname: Union[str, None] = field(default="loading")
    builder: type[Component] = field(default=html.Div)

    color: str = field(default="primary")
    type: str = field(default="border")

    def build(self) -> list[Component]:
        elements = self.flatten(element=self.element if self.element is not None else [])
        elements, hidden = self.organize(elements=elements)
        spinner_kwargs: dict[str, Any] = {"spinner_class_name": "spinner"}
        if self.color is not None: spinner_kwargs.update(color=self.color)
        if self.type is not None: spinner_kwargs.update(type=self.type)
        if self.size is not None: spinner_kwargs.update(size=self.size)
        spinner = dbc.Spinner(elements, **spinner_kwargs) if elements else dbc.Spinner(**spinner_kwargs)
        return self.serialize(elements=[self.builder(spinner, **self.arguments())], hidden=hidden)

@dataclass(kw_only=True)
class NotificationAPI(ComponentAPI):

    classname: Union[str, None] = field(default="notification")
    builder: type[Component] = field(default=dbc.Toast)

    icon: str = field(default=None)
    header: str = field(default=None)
    duration: Union[int, None] = field(default=None)
    dismissable: bool = field(default=True)
    persistence: Union[bool, str] = field(default=None)

    def __post_init__(self):
        if self.background is not None:
            self.stylename = parse_classname(classname=self.background, stylename=self.stylename)
        super().__post_init__()

    def arguments(self) -> dict:
        kwargs = super().arguments()
        header_elements = []
        if self.icon is not None:
            header_elements.extend(IconAPI(icon=self.icon).build())
        if self.header is not None:
            header_elements.extend(TextAPI(text=self.header).build())
        if header_elements:
            kwargs.update(header=html.Div(header_elements, className="title"))
        kwargs.update(duration=self.duration)
        if self.dismissable is not None: kwargs.update(dismissable=self.dismissable)
        if self.persistence is not None: kwargs.update(persistence=self.persistence)
        return kwargs

@dataclass(kw_only=True)
class ModalAPI(ComponentAPI):

    classname: Union[str, None] = field(default="modal")
    builder: type[Component] = field(default=dbc.Modal)

    header: Union[list[Component], str] = field(default=None)
    body: list[Component] = field(default_factory=list)
    footer: list[Component] = field(default_factory=list)

    size: str = field(default=None)
    fade: bool = field(default=None)
    open: bool = field(default=False)
    centered: bool = field(default=None)
    keyboard: bool = field(default=None)
    backdrop: Union[bool, str] = field(default=None)
    scrollable: bool = field(default=None)
    fullscreen: Union[bool, str] = field(default=None)

    def arguments(self) -> dict:
        kwargs = super().arguments()
        if self.size is not None: kwargs.update(size=self.size)
        if self.fade is not None: kwargs.update(fade=self.fade)
        if self.open is not None: kwargs.update(is_open=self.open)
        if self.centered is not None: kwargs.update(centered=self.centered)
        if self.keyboard is not None: kwargs.update(keyboard=self.keyboard)
        if self.backdrop is not None: kwargs.update(backdrop=self.backdrop)
        if self.scrollable is not None: kwargs.update(scrollable=self.scrollable)
        if self.fullscreen is not None: kwargs.update(fullscreen=self.fullscreen)
        return kwargs

    def build(self) -> list[Component]:
        elements = []
        if self.header is not None:
            header_elem = [dbc.ModalTitle(self.header)] if isinstance(self.header, str) else self.flatten(element=self.header)
            elements.append(dbc.ModalHeader(header_elem))
        if self.body is not None:
            elements.append(dbc.ModalBody(self.flatten(element=self.body)))
        if self.footer is not None:
            elements.append(dbc.ModalFooter(self.flatten(element=self.footer)))
        elements, hidden = self.organize(elements=elements)
        component = self.builder(elements, **self.arguments())
        return self.serialize(elements=[component], hidden=hidden)