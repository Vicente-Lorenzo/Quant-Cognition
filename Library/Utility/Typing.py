from typing import Union, Final

class Missing:
    def __repr__(self) -> str: return "Missing"
    def __bool__(self) -> bool: return False

MISSING: Final = Missing()

def isclass(obj: object) -> bool:
    return isinstance(obj, type)

def iscallable(obj: object) -> bool:
    return callable(obj)

def ismethod(obj: object) -> bool:
    import inspect
    v = obj.__func__ if isinstance(obj, (classmethod, staticmethod)) else obj
    return inspect.isroutine(v)

def isproperty(obj: object) -> bool:
    return isinstance(obj, property)

def getclass(obj: object) -> type:
    return obj if isclass(obj) else type(obj)

def getmro(obj: object) -> tuple[type, ...]:
    cls = getclass(obj)
    return cls.__mro__

def getslots(cls: object, *, mro: bool) -> tuple[str, ...]:
    cls = getclass(cls)
    classes = getmro(cls) if mro else (cls,)
    seen: set[str] = set()
    ordered: list[str] = []
    for c in classes:
        slots = c.__dict__.get("__slots__")
        if slots is None:
            continue
        names = (slots,) if isinstance(slots, str) else tuple(slots)
        for n in names:
            if isinstance(n, str) and n not in ("__dict__", "__weakref__") and n not in seen:
                seen.add(n)
                ordered.append(n)
    return tuple(ordered)

def getclasses(obj: object, *, mro: bool) -> tuple[type, ...]:
    cls = getclass(obj)
    return getmro(cls) if mro else (cls,)

def hasmember(obj: object, name: str, *, mro: bool = False, slots: bool = True) -> bool:
    if not isclass(obj):
        d = getattr(obj, "__dict__", None)
        if isinstance(d, dict) and name in d:
            return True
        if slots:
            cls = type(obj)
            if name in getslots(cls, mro=mro):
                try:
                    object.__getattribute__(obj, name)
                    return True
                except AttributeError:
                    pass
        obj = type(obj)
    for c in getclasses(obj, mro=mro):
        if name in c.__dict__:
            if not slots and name in getslots(c, mro=False):
                return False
            return True
    return False

def getmember(obj: object, name: str, *, mro: bool, slots: bool) -> tuple[bool, object]:
    d = getattr(obj, "__dict__", None)
    if isinstance(d, dict) and name in d:
        return True, d[name]
    if slots:
        cls = type(obj)
        if name in getslots(cls, mro=mro):
            try:
                return True, object.__getattribute__(obj, name)
            except AttributeError:
                pass
    return False, None

def hasattribute(obj: object, name: str, *, mro: bool = False, slots: bool = True) -> bool:
    if isclass(obj):
        for c in getclasses(obj, mro=mro):
            if name in c.__dict__:
                v = c.__dict__[name]
                if ismethod(v) or isproperty(v):
                    return False
                if not slots and name in getslots(c, mro=False):
                    return False
                return True
        return False
    found, v = getmember(obj, name, slots=slots, mro=mro)
    return found and not iscallable(v)

def getattribute(obj: object, name: str, default = None, *, mro: bool = False, slots: bool = True):
    if isclass(obj):
        for c in getclasses(obj, mro=mro):
            if name in c.__dict__:
                v = c.__dict__[name]
                if ismethod(v) or isproperty(v):
                    return default
                if not slots and name in getslots(c, mro=False):
                    return default
                return v
        return default
    found, v = getmember(obj, name, slots=slots, mro=mro)
    if not found or iscallable(v):
        return default
    return v

def hasmethod(obj: object, name: str, *, mro: bool = False, slots: bool = True) -> bool:
    if not isclass(obj):
        found, v = getmember(obj, name, slots=slots, mro=mro)
        if found and iscallable(v):
            return True
        obj = type(obj)
    for c in getclasses(obj, mro=mro):
        if name in c.__dict__ and ismethod(c.__dict__[name]):
            return True
    return False

def getmethod(obj: object, name: str, default = None, *, slots: bool = True, mro: bool = False):
    if not isclass(obj):
        found, v = getmember(obj, name, slots=slots, mro=mro)
        if found and iscallable(v):
            return v
        inst = obj
        cls = type(obj)
        for c in getclasses(cls, mro=mro):
            if name in c.__dict__ and ismethod(c.__dict__[name]):
                member = c.__dict__[name]
                return member.__get__(inst, cls) if hasattr(member, "__get__") else member
        return default
    for c in getclasses(obj, mro=mro):
        if name in c.__dict__ and ismethod(c.__dict__[name]):
            return c.__dict__[name]
    return default

def hasproperty(obj: object, name: str, *, mro: bool = False) -> bool:
    for c in getclasses(obj, mro=mro):
        if name in c.__dict__ and isproperty(c.__dict__[name]):
            return True
    return False

def getproperty(obj: object, name: str, default = None, *, mro: bool = False):
    for c in getclasses(obj, mro=mro):
        if name in c.__dict__ and isproperty(c.__dict__[name]):
            return c.__dict__[name]
    return default

def getvariable(value: object, scope: dict) -> Union[str, None]:
    for name, obj in scope.items():
        if obj is value:
            return name
    return None

def findvariable(value: object) -> Union[str, None]:
    import inspect
    frame = inspect.currentframe()
    try:
        caller = frame.f_back
        name = getvariable(value, caller.f_locals)
        if name: return name
        name = getvariable(value, caller.f_globals)
        if name: return name
        return None
    finally:
        del caller
        del frame

def cast(cast_value, cast_type: type, cast_default):
    try:
        return cast_value if isinstance(cast_value, cast_type) else cast_type(cast_value)
    except (TypeError, ValueError):
        return cast_default

def contains(text: str, substrings: Union[str, tuple, list], case_sensitive: bool = False) -> bool:
    if isinstance(substrings, str):
        subs: list[str] = [substrings]
    else:
        subs = list(substrings)
    if not case_sensitive:
        text = text.lower()
        subs = [s.lower() for s in subs]
    return any(sub in text for sub in subs)

def format(original: str, *args, **kwargs) -> str:
    from collections import defaultdict
    with_args = original.format(*args) if args else original
    with_kwargs = with_args.format_map(defaultdict(str, **kwargs)) if kwargs else with_args
    return with_kwargs