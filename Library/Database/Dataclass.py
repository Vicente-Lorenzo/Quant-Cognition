from __future__ import annotations

import dataclasses
from enum import Enum
from dataclasses import dataclass, field
from typing import Union, Type, Any, Self

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

    def __getattr__(self, item: str) -> Any:
        attrs = {k: v for base in reversed(self._cls_.mro()) if base is not object for k, v in base.__dict__.items()}
        fs = attrs.get("__dataclass_fields__", {})
        
        is_prop = item in attrs and isinstance(attrs[item], property)
        is_field = item in fs
        is_private_field = f"_{item}_" in fs or f"_{item}" in fs
        
        if not (is_prop or is_field or is_private_field):
            raise AttributeError(f"'{self._cls_.__name__}' object has no attribute '{item}'")
            
        attr_val = f"{self._name_}.{item}" if self._name_ and self._full_ else self._name_ if self._name_ else item
        
        t_str = ""
        if is_prop:
            t_str = str(attrs[item].fget.__annotations__.get("return", ""))
        elif is_field:
            t_str = str(fs[item].type)
            if "InitVar" in t_str and is_private_field:
                t_str = str(attrs.get("__annotations__", {}).get(item, ""))
        elif is_private_field:
            t_str = str(attrs.get("__annotations__", {}).get(item, ""))
            
        def get_all_subclasses(cls):
            subs = cls.__subclasses__()
            return subs + [s for sub in subs for s in get_all_subclasses(sub)]
            
        for sub in get_all_subclasses(DataclassAPI):
            if sub.__name__ in t_str:
                return DatametaAPI(cls=sub, name=attr_val, full=self._full_)
                
        return attr_val

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

    def __init_subclass__(cls, **kwargs):
        super(DataclassAPI, cls).__init_subclass__(**kwargs)
        cls.ID = DatametaAPI(cls, full=False)
        cls.OID = DatametaAPI(cls, full=True)

    def _parse_(self, name):
        f = getattr(self, name)
        if isinstance(f, Enum): return f.name
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

    def data(self, include_fields, include_initvar_fields, include_hidden_fields, include_override_fields, include_properties):
        attrs = self.__class__.__dict__
        if include_fields:
            for f_name, f in attrs.get("__dataclass_fields__", {}).items():
                if getattr(f, "_field_type", None) == getattr(dataclasses, "_FIELD_CLASSVAR", None):
                    continue
                if include_initvar_fields and getattr(f, "_field_type", None) == getattr(dataclasses, "_FIELD_INITVAR", None):
                    yield f_name, self._parse_(f_name)
                elif getattr(f, "_field_type", None) != getattr(dataclasses, "_FIELD_INITVAR", None) and (include_hidden_fields or f.repr):
                    yield f_name, self._parse_(f_name)
        if include_override_fields or include_properties:
            for cls in reversed(type(self).mro()):
                if cls is object:
                    continue
                for attr_name, attr in cls.__dict__.items():
                    if isinstance(attr, property):
                        is_field = getattr(attr.fget, "_overridefield_", False)
                        if include_override_fields and is_field:
                            yield attr_name, self._parse_(attr_name)
                        if include_properties and not is_field:
                            yield attr_name, self._parse_(attr_name)

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