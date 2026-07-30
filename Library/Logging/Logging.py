import sys
import atexit
import logging
import threading
import traceback
from time import time
from typing import Callable
from functools import wraps

from Library.Logging.Level import VerboseLevel
from Library.Logging.Logger import LoggerAPI
from Library.Logging.Console import ConsoleAPI
from Library.Logging.File import FileAPI
from Library.Logging.Storage import StorageAPI
from Library.Utility.Runtime import find_caller_frame, find_frame_class, find_frame_module, find_frame_package

VerboseLevel.register()

class LoggingAPI(logging.Logger):
    """
    The logger every module instantiates and the single place logging is configured.

    Usage is the same everywhere. Construct one, configure the sinks through it, and enter it for
    the lifetime of the work::

        log = LoggingAPI("Engine")
        log.console.set_level(VerboseLevel.Info)
        log.file.set_level(VerboseLevel.Debug)
        with log:
            log.info(lambda: "Phase Warmup: Completed · 1.20s · 205 Ticks")

    Messages are normally passed as a callable so that a record which no sink accepts costs nothing
    beyond the closure; an expensive rendering such as a dataframe is never built unless it will
    actually be written. Plain strings are accepted too, with standard library percent arguments.

    Sinks are shared class attributes, so configuring them through any instance configures them for
    the whole process and a module constructing its own logger inherits that configuration without
    coordination. Entering the context locks that configuration, which is what makes the outermost
    entry point authoritative when a master script invokes other scripts that configure logging too.

    Tags are rendered around the level: shared tags identify the run and come first, per instance
    tags identify the caller and follow. The caller identity is resolved from the calling frame, so
    nothing needs passing -- the owning object supplies the leading tag and, when no tags are given,
    the subsystem supplies the trailing one. Any tags you do pass replace that subsystem default, and
    identify=False drops the automatic identity entirely.

    The class derives from the standard library Logger, so an instance satisfies isinstance checks
    and can be handed to any third party expecting one, while the level methods below bypass the
    standard record machinery entirely for speed. LoggingAPI.install() completes the interoperation
    in the other direction by routing third party records and uncaught exceptions into these sinks.
    """

    _SEPARATOR_: str = " - "
    _PACKAGE_: str = __name__.rsplit(".", 1)[0]

    console: ConsoleAPI = ConsoleAPI()
    file: FileAPI = FileAPI()
    storage: StorageAPI = StorageAPI()

    _shared_tags_: tuple = ()
    _shared_head_: str = ""
    _depth_: int = 0

    def __init__(self, *tags, identify: bool = True) -> None:
        frame = find_caller_frame(skip=self._PACKAGE_)
        values = [value for value in tags if value is not None and str(value) != ""]
        owner = find_frame_class(frame) if identify else None
        if identify and not values:
            subsystem = find_frame_package(frame)
            if subsystem: values = [subsystem]
        if owner: values.insert(0, owner)
        super().__init__(name=owner or find_frame_module(frame) or "Python", level=logging.NOTSET)
        self.propagate = False
        self._instance_tags_: tuple = ()
        self._instance_tail_: str = ""
        self.set_instance_tags(*values)

    @property
    def SharedTags(self) -> tuple:
        """Returns the tags shared by every logger in the process."""
        return LoggingAPI._shared_tags_

    @property
    def InstanceTags(self) -> tuple:
        """Returns the tags identifying this particular logger."""
        return self._instance_tags_

    @property
    def Depth(self) -> int:
        """Returns how many nested logging contexts are currently open."""
        return LoggingAPI._depth_

    @classmethod
    def _join_(cls, values) -> str:
        rendered = [str(value) for value in values if value is not None and str(value) != ""]
        return cls._SEPARATOR_.join(rendered) + cls._SEPARATOR_ if rendered else ""

    @classmethod
    def set_shared_tags(cls, *tags) -> None:
        """
        Sets the tags shared by every logger in the process, typically the run identity.

        An empty call is ignored so a caller cannot clear them by accident; use clear_shared_tags.
        :param tags: The tags rendered before the level, in order.
        """
        values = tuple(value for value in tags if value is not None and str(value) != "")
        if not values: return
        LoggingAPI._shared_tags_ = values
        LoggingAPI._shared_head_ = cls._join_(values)

    @classmethod
    def clear_shared_tags(cls) -> None:
        """Removes the shared tags."""
        LoggingAPI._shared_tags_ = ()
        LoggingAPI._shared_head_ = ""

    def set_instance_tags(self, *tags) -> None:
        """
        Replaces the tags identifying this particular logger with exactly the ones given.

        Nothing is derived here; the automatic identity is resolved once at construction.
        :param tags: The tags rendered after the level, in order.
        """
        values = [value for value in tags if value is not None and str(value) != ""]
        self._instance_tags_ = tuple(values)
        self._instance_tail_ = self._join_(values)

    def set_level(self, level: str | int | VerboseLevel) -> None:
        """Sets the accepted level on every sink at once."""
        for sink in LoggerAPI.Registry: sink.set_level(level)

    def reset_level(self) -> None:
        """Restores the default level on every sink at once."""
        for sink in LoggerAPI.Registry: sink.reset_level()

    def open(self) -> None:
        """Opens every sink."""
        for sink in LoggerAPI.Registry: sink.open()

    def flush(self) -> None:
        """Flushes every sink."""
        for sink in LoggerAPI.Registry: sink.flush()

    def close(self) -> None:
        """Closes every sink."""
        for sink in LoggerAPI.Registry: sink.close()

    @classmethod
    def terminate(cls) -> None:
        """
        Flushes and closes every sink; registered to run once at interpreter exit.

        Sinks stay closed afterwards, so a stray record emitted while the interpreter tears itself
        down is dropped rather than reopening a file whose imports are no longer available.
        """
        for sink in LoggerAPI.Registry:
            sink.flush()
            sink.close()
        LoggerAPI.Terminated = True

    @staticmethod
    def _fallback_(error: Exception) -> None:
        stream = getattr(sys, "__stderr__", None)
        if stream is None: return
        try: stream.write(f"Logging Emit: Failed · {type(error).__name__} · {error}\n")
        except Exception: pass

    def _emit_(self, level: VerboseLevel, value: int, content, args: tuple = ()) -> None:
        try:
            message = content() if callable(content) else content
            if args: message = str(message) % args
            moment, head, tail = LoggerAPI.stamp(time()), LoggingAPI._shared_head_, self._instance_tail_
            for sink in LoggerAPI.Targets[value]: sink.write(level, moment, head, tail, message)
        except Exception as error:
            self._fallback_(error)

    def debug(self, content, *args) -> None:
        """Logs at Debug: everything that is not trading or execution."""
        if LoggerAPI.Gate < 6: return
        self._emit_(VerboseLevel.Debug, 6, content, args)

    def info(self, content, *args) -> None:
        """Logs at Info: trading, execution, and periodic trader useful information."""
        if LoggerAPI.Gate < 5: return
        self._emit_(VerboseLevel.Info, 5, content, args)

    def alert(self, content, *args) -> None:
        """Logs at Alert: conditions warranting attention but not yet a warning."""
        if LoggerAPI.Gate < 4: return
        self._emit_(VerboseLevel.Alert, 4, content, args)

    def warning(self, content, *args) -> None:
        """Logs at Warning: recoverable conditions that changed behavior."""
        if LoggerAPI.Gate < 3: return
        self._emit_(VerboseLevel.Warning, 3, content, args)

    def error(self, content, *args) -> None:
        """Logs at Error: an operation failed."""
        if LoggerAPI.Gate < 2: return
        self._emit_(VerboseLevel.Error, 2, content, args)

    def exception(self, content, *args) -> None:
        """Logs at Exception: the most severe level, conventionally carrying a traceback."""
        if LoggerAPI.Gate < 1: return
        self._emit_(VerboseLevel.Exception, 1, content, args)

    def critical(self, content, *args) -> None:
        """Logs at Exception; provided so standard library callers behave sensibly."""
        self.exception(content, *args)

    def log(self, level, content, *args) -> None:
        """
        Logs at a level chosen at runtime.
        :param level: A member, a member name, or a standard library severity; Silent is dropped.
        :param content: A callable returning the message, or the message itself.
        :param args: Optional standard library percent formatting arguments.
        """
        level = VerboseLevel.resolve(level)
        if LoggerAPI.Gate < level.value or level is VerboseLevel.Silent: return
        self._emit_(level, level.value, content, args)

    @classmethod
    def install(cls, logger: "LoggingAPI" = None, stdlib: bool = True, hooks: bool = True, level: VerboseLevel = VerboseLevel.Warning) -> "LoggingAPI":
        """
        Captures records and crashes that would otherwise never reach these sinks.

        Third party libraries log through the standard library, and uncaught exceptions go straight
        to standard error, so neither appears in the framework's own output by default. This routes
        both in. Existing hooks are chained rather than replaced, so tracebacks still print normally.
        :param logger: The logger receiving captured output; one is created when omitted.
        :param stdlib: Whether to attach the bridge to the standard library root logger.
        :param hooks: Whether to install the interpreter and thread exception hooks.
        :param level: The minimum severity captured from the standard library.
        :return: The logger receiving captured output.
        """
        logger = logger if logger is not None else cls("Runtime", "Capture", identify=False)
        logging.raiseExceptions = False
        if stdlib:
            root = logging.getLogger()
            for handler in [handler for handler in root.handlers if isinstance(handler, BridgeAPI)]: root.removeHandler(handler)
            root.addHandler(BridgeAPI(logger, level))
            if root.level == logging.NOTSET or root.level > level.Standard: root.setLevel(level.Standard)
        if hooks:
            origin, beginning = sys.excepthook, threading.excepthook
            def _excepthook_(kind, value, trace) -> None:
                logger.exception(lambda: f"Runtime Exception: Uncaught · {kind.__name__}\n{''.join(traceback.format_exception(kind, value, trace))[:-1]}")
                logger.flush()
                origin(kind, value, trace)
            def _threadhook_(arguments) -> None:
                logger.exception(lambda: f"Thread Exception: Uncaught · {arguments.thread.name if arguments.thread else 'Unknown'} · {arguments.exc_type.__name__}\n{''.join(traceback.format_exception(arguments.exc_type, arguments.exc_value, arguments.exc_traceback))[:-1]}")
                logger.flush()
                beginning(arguments)
            sys.excepthook, threading.excepthook = _excepthook_, _threadhook_
        return logger

    def __enter__(self):
        LoggingAPI._depth_ += 1
        if LoggingAPI._depth_ == 1:
            for sink in LoggerAPI.Registry:
                sink.open()
                sink.lock()
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback) -> bool:
        LoggingAPI._depth_ = max(0, LoggingAPI._depth_ - 1)
        if LoggingAPI._depth_ == 0:
            for sink in LoggerAPI.Registry:
                sink.unlock()
                sink.flush()
                sink.close()
        return False

    def guard(self, func: Callable):
        """
        Wraps a function so its lifetime is logged and its failures are recorded before propagating.

        The wrapped call runs inside this logger's context, so sinks are opened and configuration is
        locked for its duration. Exceptions are logged with their traceback and then re-raised; the
        decorator observes, it does not swallow.
        :param func: The function to wrap.
        :return: The wrapped function.
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                self.__enter__()
                self.debug(lambda: f"Initiated @ {func.__name__}")
                return func(*args, **kwargs)
            except Exception as error:
                self.exception(lambda: f"Failed @ {func.__name__}")
                self.exception(lambda: "".join(traceback.format_exception(error))[:-1])
                raise
            finally:
                self.debug(lambda: f"Terminated @ {func.__name__}")
                self.__exit__(None, None, None)
        return wrapper

class BridgeAPI(logging.Handler):
    """
    Standard library handler forwarding third party records into the framework sinks.

    Installed on the root logger by LoggingAPI.install(), this is what makes libraries that log
    through the standard library visible in the framework's own output, tracebacks included. It is
    deliberately one directional: records travel from the standard library into these sinks, never
    the other way, so there is no possibility of a loop.
    """

    def __init__(self, logger: LoggingAPI, level: VerboseLevel = VerboseLevel.Warning) -> None:
        super().__init__(level=level.Standard)
        self._logger_: LoggingAPI = logger

    @property
    def Logger(self) -> LoggingAPI:
        """Returns the framework logger receiving the forwarded records."""
        return self._logger_

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = VerboseLevel.standard(record.levelno)
            message = record.getMessage()
            if record.exc_info: message = f"{message}\n{''.join(traceback.format_exception(*record.exc_info))[:-1]}"
            self._logger_._emit_(level, level.value, f"{record.name}: {message}")
        except Exception as error:
            LoggingAPI._fallback_(error)

    def handleError(self, record: logging.LogRecord) -> None:
        pass

atexit.register(LoggingAPI.terminate)