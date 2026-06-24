import mmap
import struct
import ctypes
import ctypes.wintypes as wt
import threading

_K32_ = ctypes.windll.kernel32
_K32_.CreateEventW.argtypes = [ctypes.c_void_p, wt.BOOL, wt.BOOL, wt.LPCWSTR]
_K32_.CreateEventW.restype = wt.HANDLE
_K32_.OpenEventW.argtypes = [wt.DWORD, wt.BOOL, wt.LPCWSTR]
_K32_.OpenEventW.restype = wt.HANDLE
_K32_.SetEvent.argtypes = [wt.HANDLE]
_K32_.SetEvent.restype = wt.BOOL
_K32_.WaitForSingleObject.argtypes = [wt.HANDLE, wt.DWORD]
_K32_.WaitForSingleObject.restype = wt.DWORD
_K32_.CloseHandle.argtypes = [wt.HANDLE]
_K32_.CloseHandle.restype = wt.BOOL
_K32_.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
_K32_.OpenProcess.restype = wt.HANDLE

class PeerExit(SystemExit):
    pass

class TransportAPI:

    _INFINITE_ = 0xFFFFFFFF
    _SYNCHRONIZE_ = 0x00100000
    _EVENT_ACCESS_ = 0x00100000 | 0x0002
    _WAIT_TIMEOUT_ = 0x00000102
    _BUF_SIZE_ = 4096
    _POLL_MS_ = 500
    _LENGTH_ = struct.Struct('<I')

    def __init__(self, iid: str, create: bool = False) -> None:
        self._iid_: str = iid
        self._closed_: bool = False
        self._peer_dead_: threading.Event = threading.Event()
        prefix = f"cAlgo_{iid}"
        self._update_buf_ = mmap.mmap(-1, self._BUF_SIZE_, f"{prefix}_update")
        self._action_buf_ = mmap.mmap(-1, self._BUF_SIZE_, f"{prefix}_action")
        if create:
            self._ur_ = _K32_.CreateEventW(None, False, False, f"{prefix}_ur")
            self._uc_ = _K32_.CreateEventW(None, False, False, f"{prefix}_uc")
            self._ar_ = _K32_.CreateEventW(None, False, False, f"{prefix}_ar")
            self._ac_ = _K32_.CreateEventW(None, False, False, f"{prefix}_ac")
        else:
            self._ur_ = _K32_.OpenEventW(self._EVENT_ACCESS_, False, f"{prefix}_ur")
            self._uc_ = _K32_.OpenEventW(self._EVENT_ACCESS_, False, f"{prefix}_uc")
            self._ar_ = _K32_.OpenEventW(self._EVENT_ACCESS_, False, f"{prefix}_ar")
            self._ac_ = _K32_.OpenEventW(self._EVENT_ACCESS_, False, f"{prefix}_ac")

    @staticmethod
    def _write_(buf: mmap.mmap, data: bytes) -> None:
        if len(data) + 4 > TransportAPI._BUF_SIZE_:
            raise ValueError(f"Message too large: {len(data)} bytes exceeds buffer capacity of {TransportAPI._BUF_SIZE_ - 4}")
        buf.seek(0)
        buf.write(TransportAPI._LENGTH_.pack(len(data)))
        buf.write(data)

    @staticmethod
    def _read_(buf: mmap.mmap) -> bytes:
        buf.seek(0)
        size = TransportAPI._LENGTH_.unpack(buf.read(4))[0]
        return buf.read(size)

    def _wait_(self, handle) -> None:
        while True:
            if self._closed_:
                raise SystemExit("Transport closed")
            if self._peer_dead_.is_set():
                raise PeerExit("Peer process exited")
            result = _K32_.WaitForSingleObject(handle, self._POLL_MS_)
            if result == 0:
                return
            if result == self._WAIT_TIMEOUT_:
                continue
            raise SystemExit(f"WaitForSingleObject failed: {result}")

    def send(self, data: bytes) -> None:
        if self._closed_:
            raise SystemExit("Transport closed")
        self._write_(self._action_buf_, data)
        _K32_.SetEvent(self._ar_)
        self._wait_(self._ac_)

    def receive(self) -> bytes:
        if self._closed_:
            raise SystemExit("Transport closed")
        self._wait_(self._ur_)
        data = self._read_(self._update_buf_)
        _K32_.SetEvent(self._uc_)
        return data

    def watchdog(self, peer_pid: int) -> None:
        handle = _K32_.OpenProcess(self._SYNCHRONIZE_, False, peer_pid)
        if not handle:
            return
        def _watch_():
            _K32_.WaitForSingleObject(handle, self._INFINITE_)
            _K32_.CloseHandle(handle)
            self._peer_dead_.set()
        t = threading.Thread(target=_watch_, name="Watchdog", daemon=True)
        t.start()

    def close(self) -> None:
        if self._closed_:
            return
        self._closed_ = True
        for h in (self._ur_, self._uc_, self._ar_, self._ac_):
            if h:
                _K32_.CloseHandle(h)
        for buf in (self._update_buf_, self._action_buf_):
            if buf:
                buf.close()

__all__ = ["TransportAPI", "PeerExit"]