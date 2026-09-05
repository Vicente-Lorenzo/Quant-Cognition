from typing import Union

def memory_to_string(bytes: Union[int, float]) -> str:
    if bytes is None: return "0B"
    bytes = round(bytes)
    for unit in ["B", "kB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"]:
        bytes, remainder = divmod(bytes, 1000)
        if not bytes: return f"{remainder}{unit}"
    return f"{remainder}{unit}"