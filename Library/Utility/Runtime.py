import os
import sys
import shutil
import subprocess
from pathlib import Path
from typing import Union
from functools import lru_cache

def find_user():
    import getpass
    try:
        return getpass.getuser()
    except (OSError, KeyError, ImportError):
        return find_env_var("USER", case_sensitive=False) or find_env_var("USERNAME", case_sensitive=False)

def is_windows():
    return sys.platform.startswith("win")

def is_linux():
    return sys.platform.startswith("linux")

def is_mac():
    return sys.platform.startswith("darwin")

def is_local():
    return is_windows() or is_mac()

def is_remote():
    return is_linux()

def is_service():
    return is_remote() and not find_user()

@lru_cache(maxsize=1)
def find_ipython():
    from IPython import get_ipython
    ipython = get_ipython()
    return ipython

@lru_cache(maxsize=1)
def find_shell():
    try:
        ipython = find_ipython()
        return type(ipython).__name__ if ipython else None
    except (ImportError, AttributeError):
        return None

def is_python():
    return find_shell() is None

def is_ipython():
    return find_shell() is not None

def is_notebook():
    return find_shell() == "ZMQInteractiveShell"

def is_terminal():
    return find_shell() == "TerminalInteractiveShell"

def is_console():
    return find_shell() == "PyDevTerminalInteractiveShell"

@lru_cache(maxsize=1)
def find_notebook():
    ipython = find_ipython()
    return ipython.user_ns["__session__"]

def find_env_var(key: str, *, case_sensitive: bool = True) -> Union[str, None]:
    if key in os.environ:
        return os.environ[key]
    if case_sensitive:
        return None
    for variant in (key.lower(), key.upper(), key.capitalize(), key.title()):
        if variant in os.environ:
            return os.environ[variant]
    key = key.lower()
    for env_key, env_value in os.environ.items():
        if env_key.lower() == key:
            return env_value
    return None

def match_env_vars(*, keyword: str, case_sensitive: bool = True) -> dict[str, str]:
    matches: dict[str, str] = {}
    keyword = keyword if case_sensitive else keyword.lower()
    for env_key, env_value in os.environ.items():
        if case_sensitive:
            key_match = keyword in env_key
        else:
            key_match = keyword in env_key.lower()
        if case_sensitive:
            value_match = keyword in env_value
        else:
            value_match = keyword in env_value.lower()
        if key_match and value_match:
            matches[env_key] = env_value
    return matches

def find_host_port(*, host: str = "localhost", port_min: int = 1024, port_max: int = 65535) -> Union[int, tuple[str, int]]:
    import socket
    if not (0 <= port_min <= 65535):
        raise ValueError("Invalid min port range: [0, 65535]")
    if not (0 <= port_max <= 65535):
        raise ValueError("Invalid max port range: [0, 65535]")
    if port_min > port_max:
        raise ValueError("Invalid port range: min port cannot be larger than max port")
    for port in range(port_min, port_max + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            rc = probe.connect_ex((host, port))
            if rc != 0: return port
    raise RuntimeError(f"No free port found in range [{port_min}, {port_max}] on {host}")

def find_frame_module(frame) -> Union[str, None]:
    if frame is None: return None
    module = frame.f_globals.get("__name__", "")
    if module and module != "__main__": return module.rsplit(".", 1)[-1]
    origin = frame.f_globals.get("__file__")
    return Path(origin).stem if origin else None

def find_frame_class(frame) -> Union[str, None]:
    if frame is None: return None
    instance = frame.f_locals.get("self")
    if instance is not None: return type(instance).__name__
    owner = frame.f_locals.get("cls")
    if isinstance(owner, type): return owner.__name__
    qualname = getattr(frame.f_code, "co_qualname", "")
    if "." in qualname:
        prefix = qualname.rsplit(".", 1)[0]
        if not prefix.endswith("<locals>"): return prefix.rsplit(".", 1)[-1]
    return find_frame_module(frame)

def find_frame_package(frame, *, package: str = "Library") -> Union[str, None]:
    if frame is None: return None
    parts = [part for part in frame.f_globals.get("__name__", "").split(".") if part]
    if len(parts) >= 2: return parts[1] if parts[0] == package else parts[0]
    origin = frame.f_globals.get("__file__")
    if not origin: return None
    return Path(origin).resolve().parent.name or None

def find_caller_frame(*, depth: int = 0, skip: Union[str, None] = None):
    frame = sys._getframe(depth + 1)
    while frame is not None and skip and frame.f_globals.get("__name__", "").startswith(skip):
        frame = frame.f_back
    return frame

def find_caller_module(*, depth: int = 0, skip: Union[str, None] = None) -> Union[str, None]:
    return find_frame_module(find_caller_frame(depth=depth + 1, skip=skip))

def find_caller_class(*, depth: int = 0, skip: Union[str, None] = None) -> Union[str, None]:
    return find_frame_class(find_caller_frame(depth=depth + 1, skip=skip))

def find_caller_package(*, depth: int = 0, skip: Union[str, None] = None, package: str = "Library") -> Union[str, None]:
    return find_frame_package(find_caller_frame(depth=depth + 1, skip=skip), package=package)

def terminate(pid: Union[int, None]) -> None:
    import psutil
    if pid is None: return
    try: parent = psutil.Process(pid)
    except psutil.Error: return
    processes = parent.children(recursive=True) + [parent]
    for process in processes:
        try: process.terminate()
        except psutil.Error: pass
    for process in psutil.wait_procs(processes, timeout=5)[1]:
        try: process.kill()
        except psutil.Error: pass

def open_browser(url) -> None:
    if os.name == "nt" and shutil.which("explorer"):
        subprocess.Popen(["explorer.exe", str(url)])
        return
    import webbrowser
    webbrowser.open(str(url))

def tail_terminal(file) -> None:
    tail = f"Get-Content -LiteralPath '{file}' -Wait -Tail 200 -Encoding UTF8"
    if shutil.which("wt"): subprocess.Popen(["wt", "powershell", "-NoExit", "-Command", tail])
    else: subprocess.Popen(["powershell", "-NoExit", "-Command", tail], creationflags=subprocess.CREATE_NEW_CONSOLE)