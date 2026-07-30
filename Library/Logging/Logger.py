import sys
from abc import ABC, abstractmethod
from contextlib import contextmanager
from time import localtime, strftime

from Library.Logging.Level import VerboseLevel

class LoggerAPI(ABC):
    """
    Abstract base class for logging sinks.

    A sink owns a destination, an accepted level and the rendering of a record into a line. Every
    sink registers itself on construction, and the class keeps two derived structures that the
    façade reads on the hot path: Gate is the most verbose level any enabled sink accepts, which
    lets a suppressed record return after a single integer comparison, and Targets maps each level
    to exactly the sinks accepting it, which removes per-sink filtering from the emit loop. Both are
    rebuilt by refresh() whenever a sink's level or enablement changes.

    Subclasses implement _format_ and _write_. They must not raise; write() converts any failure
    into a diagnostic on the original standard error so that logging can never take down a caller.
    """

    _MILLISECOND_: tuple = tuple(f"{index:03d}" for index in range(1000))

    Second: int = -1
    Prefix: str = ""
    Terminated: bool = False

    Registry: list = []
    Targets: list = [[] for _ in range(7)]
    Gate: int = 0

    Name: str = None

    def __init__(self, level: VerboseLevel = VerboseLevel.Silent) -> None:
        self._level_: VerboseLevel = level
        self._default_: VerboseLevel = level
        self._enabled_: bool = True
        self._locked_: bool = False
        self._opened_: bool = False
        LoggerAPI.Registry.append(self)
        LoggerAPI.refresh()

    @property
    def Level(self) -> VerboseLevel:
        """Returns the most verbose level this sink currently accepts."""
        return self._level_

    @property
    def Default(self) -> VerboseLevel:
        """Returns the level that reset_level() restores."""
        return self._default_

    @property
    def Enabled(self) -> bool:
        """Returns whether the sink participates in dispatch at all."""
        return self._enabled_

    @property
    def Locked(self) -> bool:
        """Returns whether configuration changes are currently refused."""
        return self._locked_

    @property
    def Opened(self) -> bool:
        """Returns whether the underlying destination is open."""
        return self._opened_

    def _open_(self) -> None:
        pass

    def open(self) -> None:
        """Opens the destination if it is not already open; ignored once logging has terminated."""
        if self._opened_ or LoggerAPI.Terminated: return
        self._open_()
        self._opened_ = True

    def _close_(self) -> None:
        pass

    def close(self) -> None:
        """Closes the destination if it is open, marking it closed even if the close itself fails."""
        if not self._opened_: return
        try: self._close_()
        finally: self._opened_ = False

    def _flush_(self) -> None:
        pass

    def flush(self) -> None:
        """Pushes any buffered output to the destination, ignoring failures."""
        if not self._opened_: return
        try: self._flush_()
        except Exception: pass

    @staticmethod
    def stamp(now: float) -> str:
        """
        Renders an epoch timestamp as "YYYY-MM-DD HH:MM:SS.mmm".

        The calendar portion is recomputed only when the second changes and the millisecond suffix
        is read from a precomputed table, which makes this several times cheaper than formatting
        through datetime on every record. The value is rounded to the nearest millisecond before
        being split so that a fraction such as .1230 cannot truncate down to .122.
        :param now: Seconds since the epoch, as returned by time.time().
        :return: The formatted timestamp.
        """
        second, millisecond = divmod(int(now * 1000 + 0.5), 1000)
        if second != LoggerAPI.Second:
            LoggerAPI.Second, LoggerAPI.Prefix = second, strftime("%Y-%m-%d %H:%M:%S.", localtime(second))
        return LoggerAPI.Prefix + LoggerAPI._MILLISECOND_[millisecond]

    @classmethod
    def refresh(cls) -> None:
        """Rebuilds the shared Gate and Targets structures after any sink changes level or enablement."""
        active = [sink for sink in LoggerAPI.Registry if sink._enabled_]
        LoggerAPI.Gate = max((sink._level_.value for sink in active), default=0)
        LoggerAPI.Targets = [[sink for sink in active if sink._level_.value >= value] for value in range(7)]

    def lock(self) -> None:
        """
        Refuses further configuration changes.

        This is what makes the outermost configuration authoritative: once an entry point has
        configured its sinks and entered its logging context, a nested script calling the same
        setters is silently ignored rather than overriding it.
        """
        self._locked_ = True

    def unlock(self) -> None:
        """Accepts configuration changes again."""
        self._locked_ = False

    def enable(self) -> None:
        """Returns the sink to dispatch; ignored while locked or already enabled."""
        if self._locked_ or self._enabled_: return
        self._enabled_ = True
        LoggerAPI.refresh()

    def disable(self) -> None:
        """Removes the sink from dispatch entirely; ignored while locked or already disabled."""
        if self._locked_ or not self._enabled_: return
        self._enabled_ = False
        LoggerAPI.refresh()

    def accepts(self, level: VerboseLevel) -> bool:
        """
        Reports whether a record at the given level would reach this sink.
        :param level: The level of the hypothetical record.
        :return: True when the sink is enabled and accepts that level.
        """
        return self._enabled_ and self._level_.value >= level.value

    def set_level(self, level: str | int | VerboseLevel, default: bool = False, force: bool = False) -> None:
        """
        Sets the accepted level, skipping the work when the level is unchanged.
        :param level: A member, a member name, or a standard library severity.
        :param default: Whether this also becomes the level that reset_level() restores.
        :param force: Whether to apply the change even while locked.
        """
        level = VerboseLevel.resolve(level)
        if self._locked_ and not force: return
        if default: self._default_ = level
        if self._level_ is level: return
        self._level_ = level
        LoggerAPI.refresh()

    def set_default_level(self, level: str | int | VerboseLevel) -> None:
        """Sets the level that reset_level() restores without changing the current one."""
        if self._locked_: return
        self._default_ = VerboseLevel.resolve(level)

    def reset_level(self) -> None:
        """Restores the default level, bypassing the configuration lock."""
        self.set_level(self._default_, force=True)

    @contextmanager
    def temporary(self, level: str | int | VerboseLevel):
        """
        Applies a level for the duration of a block and then restores the previous one.

        The previous level is restored, not the default, and restoration also happens when the block
        raises. The lock is bypassed on the assumption that a caller writing this explicitly means it.
        :param level: The level to apply inside the block.
        """
        previous = self._level_
        self.set_level(level, force=True)
        try: yield self
        finally: self.set_level(previous, force=True)

    @abstractmethod
    def _format_(self, level: VerboseLevel, moment: str, head: str, tail: str, message: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def _write_(self, line: str) -> None:
        raise NotImplementedError

    def _fallback_(self, error: Exception) -> None:
        stream = getattr(sys, "__stderr__", None)
        if stream is None: return
        try: stream.write(f"Logging {self.Name} Write: Failed · {type(error).__name__} · {error}\n")
        except Exception: pass

    def write(self, level: VerboseLevel, moment: str, head: str, tail: str, message: str) -> None:
        """
        Renders a record and sends it to the destination, opening it first if needed.

        Any failure anywhere in that chain is swallowed and reported on the original standard error,
        so a broken destination degrades this sink alone and never propagates to the caller.
        :param level: The severity of the record.
        :param moment: The preformatted timestamp.
        :param head: The shared tags, already separator terminated, or an empty string.
        :param tail: The per instance tags, already separator terminated, or an empty string.
        :param message: The rendered message body.
        """
        try:
            if not self._opened_:
                if LoggerAPI.Terminated: return
                self.open()
            self._write_(self._format_(level, moment, head, tail, message))
        except Exception as error:
            self._fallback_(error)