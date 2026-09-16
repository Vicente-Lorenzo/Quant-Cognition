from typing import Union

def memory_to_string(size: Union[int, float, None]) -> str:
    size, units, index = float(size or 0), ("B", "kB", "MB", "GB", "TB", "PB"), 0
    while abs(size) >= 1024 and index < len(units) - 1: size, index = size / 1024, index + 1
    return f"{size:.0f} {units[index]}" if not index else f"{size:.1f} {units[index]}"