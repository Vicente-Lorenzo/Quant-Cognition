from __future__ import annotations

import atexit
import traceback
from abc import ABC
from typing import Callable

from Library.Utility.Profiler import Timer
from Library.Utility.Typing import MISSING, Missing

class ServiceAPI(ABC):

    def __init__(self,
                 api: ServiceAPI | Missing = MISSING,
                 **kwargs) -> None:
        super().__init__(**kwargs)

        self._api_ = api or self
        self._guard_ = None

        from Library.Logging import LoggingAPI
        self._log_: LoggingAPI = LoggingAPI()

    @property
    def _parent_(self) -> bool: return self._api_ is self

    def _connect_(self, **kwargs) -> None:
        if not self._parent_: return self._api_._connect_(**kwargs)
        raise NotImplementedError(f"{self.__class__.__name__}._connect_() is not implemented")

    def connected(self) -> bool:
        if not self._parent_: return self._api_.connected()
        raise NotImplementedError(f"{self.__class__.__name__}.connected() is not implemented")

    def connect(self, **kwargs):
        if not self._parent_: return self._api_.connect(**kwargs)
        try:
            if self.connected():
                self._log_.debug(lambda: "Connect Operation: Skipped (Already Connected)")
                return self
            if not self.disconnected():
                self._log_.warning(lambda: "Connect Operation: Disconnecting (Bad Connection)")
                self.disconnect()
            timer = Timer()
            timer.start()
            self._connect_(**kwargs)
            if not self.guarded():
                self._guard_ = self.disconnect
                try: atexit.register(self._guard_)
                except: pass
            timer.stop()
            self._log_.info(lambda: f"Connect Operation: Connected ({timer.result()})")
            return self
        except Exception as e:
            self._log_.error(lambda: f"Connect Operation: Failed · {e}")
            self._log_.exception(lambda: f"Connect Operation: Failed · {e}")
            raise

    def __enter__(self): return self.connect()

    def guarded(self) -> bool: return self._guard_ is not None

    def disconnected(self) -> bool:
        if not self._parent_: return self._api_.disconnected()
        raise NotImplementedError(f"{self.__class__.__name__}.disconnected() is not implemented")

    def _disconnect_(self) -> None:
        if not self._parent_: return self._api_._disconnect_()
        raise NotImplementedError(f"{self.__class__.__name__}._disconnect_() is not implemented")

    def disconnect(self):
        if not self._parent_: return self._api_.disconnect()
        try:
            if self.disconnected():
                self._log_.debug(lambda: "Disconnect Operation: Skipped (Already Disconnected)")
                return self
            timer = Timer()
            timer.start()
            self._disconnect_()
            timer.stop()
            if self.guarded():
                try: atexit.unregister(self._guard_)
                except: pass
                self._guard_ = None
            self._log_.info(lambda: f"Disconnect Operation: Disconnected ({timer.result()})")
            return self
        except Exception as e:
            self._log_.error(lambda: f"Disconnect Operation: Failed · {e}")
            self._log_.exception(lambda: f"Disconnect Operation: Failed · {e}")
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type or exc_val or exc_tb:
            self._log_.exception(lambda: f"Exception type: {exc_type}")
            self._log_.exception(lambda: f"Exception value: {exc_val}")
            tb_str = "".join(traceback.format_tb(exc_tb)) if exc_tb else ""
            self._log_.exception(lambda: f"Traceback:\n{tb_str}")
        self.disconnect()
        return not exc_type

    def __del__(self):
        try: self.disconnect()
        except: pass

    def _fetch_(self, callback: Callable, abort: Callable = None):
        timer = Timer()
        timer.start()
        try:
            self.connect()
            result = callback()
            return timer, result
        except Exception as e:
            if abort is not None: abort()
            self._log_.error(lambda: f"Fetch Operation: Failed · {e}")
            self._log_.exception(lambda: f"Fetch Operation: Failed · {e}")
            raise
        finally: timer.stop()

    def _execute_(self, callback: Callable, abort: Callable = None):
        timer = Timer()
        timer.start()
        try:
            self.connect()
            callback()
            return timer
        except Exception as e:
            if abort is not None: abort()
            self._log_.error(lambda: f"Execute Operation: Failed · {e}")
            self._log_.exception(lambda: f"Execute Operation: Failed · {e}")
            raise
        finally: timer.stop()