import logging
from enum import Enum

class VerboseLevel(Enum):
    """
    Framework logging severity, ordered by verbosity rather than by severity.

    A higher value means more verbose, so Debug is the largest member and Silent the smallest. A
    sink accepts a record when its own level is greater than or equal to the record's, which makes
    the comparison a single integer test on the hot path. Note this is the inverse of the standard
    library, where a higher value means more severe; Standard and standard() translate between the
    two conventions.

    The member names and values are mirrored into the C# Connector enumeration by Setup/Enum.py and
    are therefore a wire contract: neither may be renamed nor renumbered without regenerating and
    rebuilding the Connector.
    """

    Silent = 0, 60
    Exception = 1, 50
    Error = 2, 40
    Warning = 3, 30
    Alert = 4, 25
    Info = 5, 20
    Debug = 6, 10

    def __new__(cls, value: int, standard: int) -> "VerboseLevel":
        member = object.__new__(cls)
        member._value_ = value
        member._standard_ = standard
        return member

    @property
    def Standard(self) -> int:
        """Returns the equivalent standard library severity, where a higher value is more severe."""
        return self._standard_

    @classmethod
    def register(cls) -> None:
        """Publishes the framework level names to the standard library so foreign handlers render them."""
        for level in cls:
            if level is not cls.Silent: logging.addLevelName(level.Standard, level.name)

    @classmethod
    def standard(cls, value: int) -> "VerboseLevel":
        """
        Converts a standard library severity into the nearest framework level at or below it.
        :param value: A standard library severity such as logging.WARNING.
        :return: The matching framework level, falling back to Debug for anything below Info.
        """
        if value >= 60: return cls.Silent
        if value >= 50: return cls.Exception
        if value >= 40: return cls.Error
        if value >= 30: return cls.Warning
        if value >= 25: return cls.Alert
        if value >= 20: return cls.Info
        return cls.Debug

    @classmethod
    def resolve(cls, level: "str | int | VerboseLevel") -> "VerboseLevel":
        """
        Normalizes any accepted spelling of a level into the enumeration member.
        :param level: A member, a member name such as "Warning", or a standard library severity.
        :return: The matching enumeration member.
        :raises KeyError: If a name is given that is not a member.
        :raises TypeError: If the value is neither a member, a name, nor an integer.
        """
        if isinstance(level, cls): return level
        if isinstance(level, str): return cls[level]
        if isinstance(level, bool): raise TypeError("VerboseLevel Resolve: Failed · Due to unsupported type bool")
        if isinstance(level, int): return cls.standard(level)
        raise TypeError(f"VerboseLevel Resolve: Failed · Due to unsupported type {type(level).__name__}")