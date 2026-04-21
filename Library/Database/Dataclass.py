from __future__ import annotations

from typing import Type, Any
from dataclasses import dataclass, field, InitVar
from enum import Enum

from Library.Utility.Typing import MISSING

def overridefield(func):
    func._overridefield_ = True
    return func

class DatametaAPI:

    def __init__(self, cls: Type, iid: str | None = None):
        self._cls = cls
        self._iid = iid

    def __getattr__(self, item: str):
        attrs: dict[str, Any] = {
            k: v
            for base in reversed(self._cls.mro())
            if base is not object
            for k, v in base.__dict__.items()
        }
        def get_attribute_type(name: str) -> type | None:
            ann = attrs.get("__annotations__", {})
            return ann.get(name, None)
        def get_property_type(name: str) -> type | None:
            prop = attrs.get(name, None)
            if isinstance(prop, property):
                return prop.fget.__annotations__.get("return", None)
            return None
        fs = attrs.get("__dataclass_fields__")
        if fs is not None and (f := fs.get(item, None)) is not None:
            if isinstance(f.type, InitVar):
                ft = get_property_type(name=item)
            elif item.startswith("_"):
                item_name = item[1:]
                if item_name.endswith("_"): item_name = item_name[:-1]
                ft = get_property_type(name=item_name)
            else:
                ft = f.type
            iid = f"{self._iid}.{item}" if self._iid else item
            if isinstance(ft, type) and issubclass(ft, DataclassAPI):
                return DatametaAPI(cls=ft, iid=iid)
            return iid
        if (a := attrs.get(item, None)) is not None:
            if isinstance(a, property):
                at = get_property_type(item)
            else:
                at = get_attribute_type(item)
            iid = f"{self._iid}.{item}" if self._iid else item
            if isinstance(at, type) and issubclass(at, DataclassAPI):
                return DatametaAPI(cls=at, iid=iid)
            return iid
        raise AttributeError(f"'{self._cls.__name__}' object has no attribute '{item}'")

    def __repr__(self) -> str:
        return repr(self._iid if self._iid else self._cls.__name__)

@dataclass(slots=True)
class DataclassAPI:

    UID: Any = field(default=MISSING, kw_only=True)

    def __init_subclass__(cls, **kwargs):
        super(DataclassAPI, cls).__init_subclass__(**kwargs)
        cls.ID = DatametaAPI(cls)

    def parse(self, name):
        f = getattr(self, name)
        if isinstance(f, Enum): return f.name
        if isinstance(f, DataclassAPI) and (uid := f.UID) is not MISSING: return uid
        return f

    def data(self, include_fields, include_initvar_fields, include_hidden_fields, include_override_fields, include_properties):
        attrs = self.__class__.__dict__
        if include_fields:
            for f_name, f in attrs.get("__dataclass_fields__", {}).items():
                if include_initvar_fields and isinstance(f.type, InitVar):
                    yield f_name, self.parse(f_name)
                elif not isinstance(f.type, InitVar) and (include_hidden_fields or f.repr):
                    yield f_name, self.parse(f_name)
        if include_override_fields or include_properties:
            for cls in reversed(type(self).mro()):
                if cls is object:
                    continue
                for attr_name, attr in cls.__dict__.items():
                    if isinstance(attr, property):
                        is_field = getattr(attr.fget, "_overridefield_", False)
                        if include_override_fields and is_field:
                            yield attr_name, self.parse(attr_name)
                        if include_properties and not is_field:
                            yield attr_name, self.parse(attr_name)

    def tuple(self, include_fields=True, include_initvar_fields=False, include_hidden_fields=False, include_override_fields=True, include_properties=False):
        return tuple([v for _, v in self.data(
            include_fields=include_fields,
            include_initvar_fields=include_initvar_fields,
            include_hidden_fields=include_hidden_fields,
            include_override_fields=include_override_fields,
            include_properties=include_properties
        )])

    def list(self, include_fields=True, include_initvar_fields=False, include_hidden_fields=False, include_override_fields=True, include_properties=False):
        return list([v for _, v in self.data(
            include_fields=include_fields,
            include_initvar_fields=include_initvar_fields,
            include_hidden_fields=include_hidden_fields,
            include_override_fields=include_override_fields,
            include_properties=include_properties
        )])

    def dict(self, include_fields=True, include_initvar_fields=False, include_hidden_fields=False, include_override_fields=True, include_properties=False):
        return dict({k: v for k, v in self.data(
            include_fields=include_fields,
            include_initvar_fields=include_initvar_fields,
            include_hidden_fields=include_hidden_fields,
            include_override_fields=include_override_fields,
            include_properties=include_properties
        )})