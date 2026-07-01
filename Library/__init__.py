import os

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
if os.name == "nt":
    try:
        import ctypes
        import importlib.util
        _torch_ = importlib.util.find_spec("torch")
        if _torch_ is not None and _torch_.origin is not None:
            ctypes.CDLL(os.path.join(os.path.dirname(_torch_.origin), "lib", "libiomp5md.dll"))
    except Exception:
        pass