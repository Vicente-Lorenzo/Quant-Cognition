from __future__ import annotations

import json
import functools
import dataclasses
from enum import Enum
from dataclasses import dataclass, field
from typing import Union, Type, Any, ClassVar, Self

from Library.Utility.Typing import MISSING

def overridefield(func):
    func._overridefield_ = True
    return func

def coerce(value: Any) -> Any:
    return MISSING if isinstance(value, property) else value

class DatametaAPI:

    def __init__(self, cls: Type, name: Union[str, None] = None, full: bool = False):
        self._cls_ = cls
        self._name_ = name
        self._full_ = full

    @staticmethod
    @functools.cache
    def _resolve_(cls: Type, name: Union[str, None], full: bool, item: str) -> Any:
        attrs = {k: v for base in reversed(cls.mro()) if base is not object for k, v in base.__dict__.items()}
        fs = attrs.get("__dataclass_fields__", {})
        is_prop = item in attrs and isinstance(attrs[item], property)
        is_field = item in fs
        is_private_field = f"_{item}_" in fs or f"_{item}" in fs
        if not (is_prop or is_field or is_private_field):
            raise AttributeError(f"'{cls.__name__}' object has no attribute '{item}'")
        attr_val = f"{name}.{item}" if name and full else name if name else item
        t_str = ""
        if is_prop:
            t_str = str(attrs[item].fget.__annotations__.get("return", ""))
        elif is_field:
            t_str = str(fs[item].type)
            if "InitVar" in t_str and is_private_field:
                t_str = str(attrs.get("__annotations__", {}).get(item, ""))
        elif is_private_field:
            t_str = str(attrs.get("__annotations__", {}).get(item, ""))
        result = attr_val
        def get_all_subclasses(c):
            subs = c.__subclasses__()
            return subs + [s for child in subs for s in get_all_subclasses(child)]
        for child_class in get_all_subclasses(DataclassAPI):
            if child_class.__name__ in t_str:
                result = DatametaAPI(cls=child_class, name=attr_val, full=full)
                break
        return result

    def __getattr__(self, item: str) -> Any:
        return self._resolve_(self._cls_, self._name_, self._full_, item)

    def __str__(self) -> str:
        return self._name_ if self._name_ else self._cls_.__name__

    def __repr__(self) -> str:
        return repr(self._name_ if self._name_ else self._cls_.__name__)

    def __eq__(self, other: Any) -> bool:
        return str(self) == str(other)

    def __hash__(self) -> int:
        return hash(str(self))

@dataclass
class DataclassAPI:

    UID: Any = field(default=MISSING, kw_only=True)

    _flatten_: ClassVar[tuple[str, ...]] = ()

    def __init_subclass__(cls, **kwargs):
        super(DataclassAPI, cls).__init_subclass__(**kwargs)
        cls.ID = DatametaAPI(cls, full=False)
        cls.OID = DatametaAPI(cls, full=True)

    def _parse_(self, name, flatten=False):
        f = getattr(self, name)
        if isinstance(f, Enum): return f.name
        if flatten and name in self._flatten_ and isinstance(f, DataclassAPI): return f
        if isinstance(f, DataclassAPI) and (uid := f.UID) is not MISSING: return uid
        return f

    @classmethod
    def initvars(cls) -> set[str]:
        return {name for name, f in cls.__dataclass_fields__.items()
                if f.init and getattr(f, "_field_type", None) != getattr(dataclasses, "_FIELD_CLASSVAR", None)}

    @classmethod
    def fields(cls) -> set[str]:
        return {name for name, f in cls.__dataclass_fields__.items()
                if getattr(f, "_field_type", None) != getattr(dataclasses, "_FIELD_CLASSVAR", None)}

    @classmethod
    def parse(cls, data: Union[tuple, list, dict], **overrides) -> Self:
        if isinstance(data, dict):
            valid = cls.initvars()
            kwargs = {k: v for k, v in data.items() if k in valid}
            kwargs.update(overrides)
            return cls(**kwargs)
        return cls(*data, **overrides)

    def update(self, **kwargs) -> Self:
        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)
        return self

    def data(self, include_fields=True, include_initvar_fields=False, include_hidden_fields=False, include_override_fields=True, include_properties=False, flatten=False):
        attrs = self.__class__.__dict__
        def _yield_(name):
            val = self._parse_(name, flatten=flatten)
            if flatten and isinstance(val, DataclassAPI):
                for sub_k, sub_v in val.data(include_fields, include_initvar_fields, include_hidden_fields, include_override_fields, include_properties, flatten):
                    yield f"{name}.{sub_k}", sub_v
            else:
                yield name, val
        if include_fields:
            for f_name, f in attrs.get("__dataclass_fields__", {}).items():
                if getattr(f, "_field_type", None) == getattr(dataclasses, "_FIELD_CLASSVAR", None):
                    continue
                if include_initvar_fields and getattr(f, "_field_type", None) == getattr(dataclasses, "_FIELD_INITVAR", None):
                    yield from _yield_(f_name)
                elif getattr(f, "_field_type", None) != getattr(dataclasses, "_FIELD_INITVAR", None) and (include_hidden_fields or f.repr):
                    yield from _yield_(f_name)
        if include_override_fields or include_properties:
            for cls in reversed(type(self).mro()):
                if cls is object:
                    continue
                for attr_name, attr in cls.__dict__.items():
                    if isinstance(attr, property):
                        is_field = getattr(attr.fget, "_overridefield_", False)
                        if include_override_fields and is_field:
                            yield from _yield_(attr_name)
                        if include_properties and not is_field:
                            yield from _yield_(attr_name)

    def tuple(self, include_fields=True, include_initvar_fields=False, include_hidden_fields=False, include_override_fields=True, include_properties=False, flatten=False):
        return tuple([v for _, v in self.data(
            include_fields=include_fields,
            include_initvar_fields=include_initvar_fields,
            include_hidden_fields=include_hidden_fields,
            include_override_fields=include_override_fields,
            include_properties=include_properties,
            flatten=flatten
        )])

    def list(self, include_fields=True, include_initvar_fields=False, include_hidden_fields=False, include_override_fields=True, include_properties=False, flatten=False):
        return list([v for _, v in self.data(
            include_fields=include_fields,
            include_initvar_fields=include_initvar_fields,
            include_hidden_fields=include_hidden_fields,
            include_override_fields=include_override_fields,
            include_properties=include_properties,
            flatten=flatten
        )])

    def dict(self, include_fields=True, include_initvar_fields=False, include_hidden_fields=False, include_override_fields=True, include_properties=False, flatten=False):
        return dict({k: v for k, v in self.data(
            include_fields=include_fields,
            include_initvar_fields=include_initvar_fields,
            include_hidden_fields=include_hidden_fields,
            include_override_fields=include_override_fields,
            include_properties=include_properties,
            flatten=flatten
        )})

    def json(self, include_fields=True, include_initvar_fields=False, include_hidden_fields=False, include_override_fields=True, include_properties=False, flatten=False, **extras) -> str:
        d = self.dict(include_fields=include_fields, include_initvar_fields=include_initvar_fields, include_hidden_fields=include_hidden_fields, include_override_fields=include_override_fields, include_properties=include_properties, flatten=flatten)
        d.update(extras)
        return json.dumps({k: v for k, v in d.items() if v is not None and v is not MISSING})