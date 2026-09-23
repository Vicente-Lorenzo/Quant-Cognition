from typing import Any, Union

class SecretAPI:

    MASK: str = "***"

    def __init__(self, value: Union[str, None] = None) -> None:
        self._value_ = value

    def __repr__(self) -> str:
        return self.MASK

    def __str__(self) -> str:
        return self.MASK

    def __bool__(self) -> bool:
        return bool(self._value_)

    def __eq__(self, other: Any) -> bool:
        return self._value_ == (other._value_ if isinstance(other, SecretAPI) else other)

    def __hash__(self) -> int:
        return hash(self._value_)

    @property
    def Value(self) -> Union[str, None]:
        return self._value_

    @classmethod
    def wrap(cls, values: dict) -> dict:
        return {name: cls(value) for name, value in values.items()}

    @classmethod
    def unwrap(cls, values: dict) -> dict:
        return {name: value.Value if isinstance(value, cls) else value for name, value in values.items()}

    @classmethod
    def mask(cls, values: dict) -> dict:
        return {name: cls.MASK for name in values}