import os
import sys
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