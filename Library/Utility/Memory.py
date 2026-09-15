from typing import Union

def memory_to_string(size: Union[int, float]) -> str:
    if size is None: return "0B"
    size = round(size)
    for unit in ["B", "kB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"]:
        size, remainder = divmod(size, 1000)
        if not size: return f"{remainder}{unit}"
    return f"{remainder}{unit}"