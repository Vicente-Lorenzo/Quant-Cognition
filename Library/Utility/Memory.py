import os
import pickle

from typing import Any, Union
from multiprocessing.shared_memory import SharedMemory

def memory_to_string(size: Union[int, float, None]) -> str:
    size, units, index = float(size or 0), ("B", "kB", "MB", "GB", "TB", "PB"), 0
    while abs(size) >= 1024 and index < len(units) - 1: size, index = size / 1024, index + 1
    return f"{size:.0f} {units[index]}" if not index else f"{size:.1f} {units[index]}"

class BlockAPI(SharedMemory):

    def __init__(self, name: Union[str, None] = None, create: bool = False, size: int = 0) -> None:
        super().__init__(name=name, create=create, size=size)
        if not create and os.name == "posix":
            from multiprocessing import resource_tracker
            resource_tracker.unregister(self._name, "shared_memory")

    def __del__(self) -> None:
        try: self.close()
        except (BufferError, OSError): pass

class ParcelAPI:

    def __init__(self, value: Any) -> None:
        data = pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
        self._block_ = BlockAPI(create=True, size=max(1, len(data)))
        self._block_.buf[:len(data)] = data
        self._size_ = len(data)

    @staticmethod
    def attach(handle: tuple[str, int]) -> Any:
        name, size = handle
        block = BlockAPI(name=name)
        try:
            with block.buf[:size] as view: return pickle.loads(view)
        finally: block.close()

    def handle(self) -> tuple[str, int]:
        return self._block_.name, self._size_

    def close(self) -> None:
        self._block_.unlink()
        try: self._block_.close()
        except BufferError: pass