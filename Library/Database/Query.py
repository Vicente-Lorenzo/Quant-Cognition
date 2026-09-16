from __future__ import annotations

import re
from typing import Union, Callable

from Library.Utility.File import FileAPI
from Library.Utility.Typing import format

class QueryAPI(FileAPI):
    """
    Handles SQL query compilation, parameter binding, and execution.
    """

    Interpolation: str = "::"
    Named: str = ":"
    Positional: str = ":?:"

    _INTERPOLATION_PARAMETER_TOKEN_ = re.compile(r"::([A-Za-z_]\w*)::")
    _NAMED_PARAMETER_TOKEN_ = re.compile(r":([A-Za-z_]\w*):")
    _POSITIONAL_PARAMETER_TOKEN_ = re.compile(r":\?:")
    _PARAMETER_TOKEN_ = re.compile(rf"{_POSITIONAL_PARAMETER_TOKEN_.pattern}|{_NAMED_PARAMETER_TOKEN_.pattern}")

    @classmethod
    def named(cls, name: str) -> str:
        """
        Renders the named placeholder for a parameter.
        :param name: The parameter name.
        :return: The placeholder, as in :name:.
        """
        return f"{cls.Named}{name}{cls.Named}"

    def compile(self, token: Callable[[int], str], **kwargs) -> tuple[str, list[Union[int, str]]]:
        """
        Compiles the SQL query by replacing placeholders with appropriate tokens.
        :param token: A callable that returns a parameter token based on index.
        :param kwargs: Named parameters for interpolation.
        :return: A tuple containing the compiled query string and a configuration list.
        """
        query = str(self)
        interpolation = set(self._INTERPOLATION_PARAMETER_TOKEN_.findall(query))
        if interpolation:
            missing = interpolation.difference(kwargs.keys())
            if missing:
                k = next(iter(missing))
                raise KeyError(f"Missing interpolation parameter '{k}' for ::{k}:: placeholder")
            query = self._INTERPOLATION_PARAMETER_TOKEN_.sub(r"{\1}", query)
            query = format(query, **kwargs)
        configuration: list[Union[int, str]] = []
        parameters_index: int = 0
        positional_index: int = 0
        query_parts: list[str] = []
        query_cursor: int = 0
        for match in self._PARAMETER_TOKEN_.finditer(query):
            query_parts.append(query[query_cursor:match.start()])
            parameters_index += 1
            query_parts.append(token(parameters_index))
            name = match.group(1)
            if name is not None:
                configuration.append(name)
            else:
                configuration.append(positional_index)
                positional_index += 1
            query_cursor = match.end()
        query_parts.append(query[query_cursor:])
        query = "".join(query_parts)
        return query, configuration

    @staticmethod
    def bind(configuration: list[Union[int, str]], *args, **kwargs) -> tuple:
        """
        Binds positional and named arguments to the query configuration.
        :param configuration: A list of parameter specifications from compile.
        :param args: Positional arguments to bind.
        :param kwargs: Named arguments to bind.
        :return: A tuple of parameters ready for database execution.
        """
        args = args or ()
        kwargs = kwargs or {}
        parameters = []
        for spec in configuration:
            match spec:
                case int() as i:
                    if i >= len(args):
                        raise ValueError("Not enough positional parameters for :?: placeholders")
                    parameters.append(args[i])
                case str() as k:
                    if k not in kwargs:
                        raise KeyError(f"Missing named parameter '{k}' for :{k}: placeholder")
                    parameters.append(kwargs[k])
        return tuple(parameters)

    def __add__(self, other: Union[str, QueryAPI]) -> QueryAPI:
        left = str(self).rstrip().rstrip(";").rstrip()
        right = str(other).lstrip().lstrip(";").lstrip()
        return QueryAPI(f"{left}; {right}")

    def __iadd__(self, other: Union[str, QueryAPI]) -> QueryAPI:
        return self.__add__(other)

    def __call__(self, token: Callable[[int], str], *args, **kwargs) -> tuple[str, list[Union[int, str]], tuple | None]:
        query, configuration = self.compile(token, **kwargs)
        parameters = self.bind(configuration, *args, **kwargs) if configuration else None
        return query, configuration, parameters