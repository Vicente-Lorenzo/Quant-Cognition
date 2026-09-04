import shlex
from typing import Any, Callable
from dataclasses import dataclass, field

from Library.App.V2.Core.Callback import ComponentID
from Library.App.V2.Component.Component import Component, InputAPI, SelectAPI, SwitchAPI, TextareaAPI
from Library.Utility.Enumeration import EnumerationAPI

class ControlType(EnumerationAPI):
    Text = "text"
    Number = "number"
    Select = "select"
    Switch = "switch"
    Textarea = "textarea"

@dataclass(kw_only=True, eq=False)
class FieldAPI:

    name: str
    label: str = None
    column: str = None
    control: ControlType | str = ControlType.Text
    help: str = None
    placeholder: str = None
    options: list = field(default_factory=list)
    default: Any = None
    minimum: int | float = None
    step: int | float = None
    flag: str = None
    identity: bool = False
    required: bool = False
    stored: bool = True
    rendered: bool = True
    group: str = None
    wrapper: str = None
    suffix: Callable = None
    decode: Callable = None
    encode: Callable = None

    def __post_init__(self):
        self.control = self.control if isinstance(self.control, ControlType) else ControlType(self.control)
        self.attribute = f"F_{self.name.upper()}"
        self.id = ComponentID()
        self.id.name = self.attribute
        if self.flag is None: self.flag = "--" + self.name.replace("_", "-")
        if self.label is None: self.label = self.name.replace("_", " ").title()
        if self.column is None: self.column = self.label.replace(" ", "")

    @property
    def switched(self) -> bool:
        return self.control is ControlType.Switch

    def bind(self, page) -> dict:
        return getattr(page, self.attribute)

    def initial(self, page):
        return self.default(page) if callable(self.default) else self.default

    def build(self, page, **over) -> list[Component]:
        identifier = self.bind(page)
        value = self.initial(page)
        if self.control is ControlType.Select:
            return SelectAPI(id=identifier, options=self.options, value=value, **over).build()
        if self.control is ControlType.Switch:
            return SwitchAPI(id=identifier, label=self.label, value=value, **over).build()
        if self.control is ControlType.Textarea:
            return TextareaAPI(id=identifier, value=value, **over).build()
        return InputAPI(id=identifier, type=self.control.value, placeholder=self.placeholder, value=value, min=self.minimum, step=self.step, **over).build()

    def read(self, row: dict, page=None):
        if self.decode: return self.decode(row)
        value = row.get(self.column)
        if self.switched: return value is not False if self.initial(page) else bool(value)
        return self.initial(page) if value is None else value

    def write(self, value):
        if self.encode: return self.encode(value)
        if self.switched: return bool(value)
        if self.control is ControlType.Number: return value or 0
        return value or None

    def argument(self, value) -> list:
        if self.switched: return [self.flag] if value else []
        if value is None or value == "": return []
        return [self.flag, str(value)]

    @staticmethod
    def command(fields, values, *leading) -> str:
        parts = list(leading)
        for entry, value in zip(fields, values): parts += entry.argument(value)
        return " ".join(part if " " not in part else f'"{part}"' for part in parts)

    @staticmethod
    def parse(fields, arguments) -> dict:
        flags = {entry.flag: entry for entry in fields}
        parsed, tokens, index = {}, shlex.split(arguments or "", posix=False), 0
        while index < len(tokens):
            entry = flags.get(tokens[index].strip('"'))
            if entry is None:
                index += 1
                continue
            if entry.switched:
                parsed[entry.label or entry.name] = "Yes"
                index += 1
                continue
            value = tokens[index + 1].strip('"') if index + 1 < len(tokens) else ""
            parsed[entry.label or entry.name] = "" if value in flags else value
            index += 2 if value not in flags else 1
        return parsed

    @staticmethod
    def index(fields) -> dict:
        return {entry.name: entry for entry in fields}

    @staticmethod
    def payload(fields, values) -> dict:
        return {entry.column: entry.write(value) for entry, value in zip(fields, values) if entry.stored and not entry.identity}

    @staticmethod
    def missing(fields, values) -> str | None:
        absent = [entry.label for entry, value in zip(fields, values) if entry.required and not value]
        if not absent: return None
        return absent[0] if len(absent) == 1 else f"{', '.join(absent[:-1])} and {absent[-1]}"