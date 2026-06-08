import sys
from os import getcwd
from typing import Union
from sys import _getframe
from pathlib import PurePath, Path
from re import Pattern, compile, search
from dataclasses import dataclass, field, InitVar

from Library.Utility.Typing import contains
from Library.Utility.Runtime import is_notebook, find_notebook

def inspect_separator(*, builder: type[PurePath] = Path) -> str:
    return str(builder("a", "b"))[1]

def inspect_file(file: Union[PurePath, str, None], *, header: bool = None, resolve: bool = False, builder: type[PurePath] = Path) -> Union[PurePath, Path]:
    sep: str = inspect_separator(builder=builder)
    file: str = str(file) if file else ""
    if header is True:
        file: PurePath = builder(sep) / builder(file)
    elif header is False:
        file: PurePath = builder(file.lstrip(sep))
    else:
        file: PurePath = builder(file)
    return file.resolve() if (isinstance(file, Path) and resolve) else file

def inspect_path(file: PurePath, *, footer: bool = None) -> str:
    sep: str = inspect_separator(builder=type(file))
    file: str = str(file)
    if footer is True:
        return file + sep if set(file) != set(sep) else file
    elif footer is False:
        return file.rstrip(sep)
    else:
        return file

def inspect_file_path(file: Union[PurePath, str, None], *, header: bool = None, footer: bool = None, resolve: bool = False, builder: type[PurePath] = Path) -> str:
    path: PurePath = inspect_file(file=file, header=header, resolve=resolve, builder=builder)
    return inspect_path(file=path, footer=footer)

def inspect_module(file: Union[PurePath, str, None], *, header: bool = None, resolve: bool = False, builder: type[PurePath] = Path) -> Union[PurePath, Path]:
    path: PurePath = inspect_file(file=file, header=header, resolve=resolve, builder=builder)
    return path.parent if path.suffix else path

def inspect_module_path(file: Union[str, None], *, header: bool = None, footer: bool = None, resolve: bool = False, builder: type[PurePath] = Path) -> str:
    module: PurePath = inspect_module(file=file, header=header, resolve=resolve, builder=builder)
    return inspect_path(file=module, footer=footer)

def traceback_working() -> str:
    return getcwd()

def traceback_working_module(*, header: bool = None, resolve: bool = False, builder: type[PurePath] = Path) -> Union[PurePath, Path]:
    traceback: str = traceback_working()
    return inspect_module(file=traceback, header=header, resolve=resolve, builder=builder)

def traceback_working_module_path(*, header: bool = None, footer: bool = None, resolve: bool = False, builder: type[PurePath] = Path) -> str:
    traceback: str = traceback_working()
    return inspect_module_path(file=traceback, header=header, footer=footer, resolve=resolve, builder=builder)

def traceback_depth(*, depth: int = 1) -> Union[str, None]:
    f: str = _getframe(depth).f_code.co_filename
    if f.startswith("<") and f.endswith(">"):
        return find_notebook() if is_notebook() else traceback_working()
    if contains(f, ("ipython", "ipykernel", "interactiveshell", "runpy")):
        return find_notebook() if is_notebook() else f
    return f

def traceback_depth_file(*, header: bool = None, resolve: bool = False, builder: type[PurePath] = Path, depth: int = 2) -> Union[PurePath, Path]:
    traceback: str = traceback_depth(depth=depth)
    return inspect_file(file=traceback, header=header, resolve=resolve, builder=builder)

def traceback_depth_file_path(*, header: bool = None, footer: bool = None, resolve: bool = False, builder: type[PurePath] = Path, depth: int = 2) -> str:
    traceback: str = traceback_depth(depth=depth)
    return inspect_file_path(file=traceback, header=header, footer=footer, resolve=resolve, builder=builder)

def traceback_depth_module(*, header: bool = None, resolve: bool = False, builder: type[PurePath] = Path, depth: int = 2) -> Union[PurePath, Path]:
    traceback: str = traceback_depth(depth=depth)
    return inspect_module(file=traceback, header=header, resolve=resolve, builder=builder)

def traceback_depth_module_path(*, header: bool = None, footer: bool = None, resolve: bool = False, builder: type[PurePath] = Path, depth: int = 2) -> str:
    traceback: str = traceback_depth(depth=depth)
    return inspect_module_path(file=traceback, header=header, footer=footer, resolve=resolve, builder=builder)

def traceback_origin() -> str:
    depth: int = 0
    try:
        while origin := traceback_depth(depth=depth):
            depth += 1
    except ValueError:
        depth -= 1
        origin = traceback_depth(depth=depth)
    return origin

def traceback_origin_file(*, header: bool = None, resolve: bool = False, builder: type[PurePath] = Path) -> Union[PurePath, Path]:
    traceback: str = traceback_origin()
    return inspect_file(file=traceback, header=header, resolve=resolve, builder=builder)

def traceback_origin_file_path(*, header: bool = None, footer: bool = None, resolve: bool = False, builder: type[PurePath] = Path) -> str:
    traceback: str = traceback_origin()
    return inspect_file_path(file=traceback, header=header, footer=footer, resolve=resolve, builder=builder)

def traceback_origin_module(*, header: bool = None, resolve: bool = False, builder: type[PurePath] = Path) -> Union[PurePath, Path]:
    traceback: str = traceback_origin()
    return inspect_module(file=traceback, header=header, resolve=resolve, builder=builder)

def traceback_origin_module_path(*, header: bool = None, footer: bool = None, resolve: bool = False, builder: type[PurePath] = Path) -> str:
    traceback: str = traceback_origin()
    return inspect_module_path(file=traceback, header=header, footer=footer, resolve=resolve, builder=builder)

def traceback_current():
    depth: int = 0
    while current := traceback_depth(depth=depth):
        if current != __file__: break
        depth += 1
    return current

def traceback_current_file(*, header: bool = None, resolve: bool = False, builder: type[PurePath] = Path) -> Union[PurePath, Path]:
    traceback: str = traceback_current()
    return inspect_file(file=traceback, header=header, resolve=resolve, builder=builder)

def traceback_current_file_path(*, header: bool = None, footer: bool = None, resolve: bool = False, builder: type[PurePath] = Path) -> str:
    traceback: str = traceback_current()
    return inspect_file_path(file=traceback, header=header, footer=footer, resolve=resolve, builder=builder)

def traceback_current_module(*, header: bool = None, resolve: bool = False, builder: type[PurePath] = Path) -> Union[PurePath, Path]:
    traceback: str = traceback_current()
    return inspect_module(file=traceback, header=header, resolve=resolve, builder=builder)

def traceback_current_module_path(*, header: bool = None, footer: bool = None, resolve: bool = False, builder: type[PurePath] = Path) -> str:
    traceback: str = traceback_current()
    return inspect_module_path(file=traceback, header=header, footer=footer, resolve=resolve, builder=builder)

def traceback_calling() -> str:
    depth: int = 0
    current: str = traceback_current()
    while calling := traceback_depth(depth=depth):
        if calling != __file__ and calling != current: break
        depth += 1
    return calling

def traceback_calling_file(*, header: bool = None, resolve: bool = False, builder: type[PurePath] = Path) -> Union[PurePath, Path]:
    traceback: str = traceback_calling()
    return inspect_file(file=traceback, header=header, resolve=resolve, builder=builder)

def traceback_calling_file_path(*, header: bool = None, footer: bool = None, resolve: bool = False, builder: type[PurePath] = Path) -> str:
    traceback: str = traceback_calling()
    return inspect_file_path(file=traceback, header=header, footer=footer, resolve=resolve, builder=builder)

def traceback_calling_module(*, header: bool = None, resolve: bool = False, builder: type[PurePath] = Path) -> Union[PurePath, Path]:
    traceback: str = traceback_calling()
    return inspect_module(file=traceback, header=header, resolve=resolve, builder=builder)

def traceback_calling_module_path(*, header: bool = None, footer: bool = None, resolve: bool = False, builder: type[PurePath] = Path) -> str:
    traceback: str = traceback_calling()
    return inspect_module_path(file=traceback, header=header, footer=footer, resolve=resolve, builder=builder)

def traceback_regex(*, pattern: str) -> str:
    depth: int = 0
    pattern: Pattern = compile(pattern)
    while not search(pattern, expression := traceback_depth(depth=depth)):
        depth += 1
    return expression

def traceback_regex_file(pattern: str, *, header: bool = None, resolve: bool = False, builder: type[PurePath] = Path) -> Union[PurePath, Path]:
    traceback: str = traceback_regex(pattern=pattern)
    return inspect_file(file=traceback, header=header, resolve=resolve, builder=builder)

def traceback_regex_file_path(pattern: str, *, header: bool = None, footer: bool = None, resolve: bool = False, builder: type[PurePath] = Path) -> str:
    traceback: str = traceback_regex(pattern=pattern)
    return inspect_file_path(file=traceback, header=header, footer=footer, resolve=resolve, builder=builder)

def traceback_regex_module(pattern: str, *, header: bool = None, resolve: bool = False, builder: type[PurePath] = Path) -> Union[PurePath, Path]:
    traceback: str = traceback_regex(pattern=pattern)
    return inspect_module(file=traceback, header=header, resolve=resolve, builder=builder)

def traceback_regex_module_path(pattern: str, *, header: bool = None, footer: bool = None, resolve: bool = False, builder: type[PurePath] = Path) -> str:
    traceback: str = traceback_regex(pattern=pattern)
    return inspect_module_path(file=traceback, header=header, footer=footer, resolve=resolve, builder=builder)

def traceback_package(*, package: str) -> str:
    return sys.modules[package].__file__

def traceback_package_file(package: str, *, header: bool = None, resolve: bool = False, builder: type[PurePath] = Path) -> Union[PurePath, Path]:
    traceback: str = traceback_package(package=package)
    return inspect_file(file=traceback, header=header, resolve=resolve, builder=builder)

def traceback_package_file_path(package: str, *, header: bool = None, footer: bool = None, resolve: bool = False, builder: type[PurePath] = Path) -> str:
    traceback: str = traceback_package(package=package)
    return inspect_file_path(file=traceback, header=header, footer=footer, resolve=resolve, builder=builder)

def traceback_package_module(package: str, *, header: bool = None, resolve: bool = False, builder: type[PurePath] = Path) -> Union[PurePath, Path]:
    traceback: str = traceback_package(package=package)
    return inspect_module(file=traceback, header=header, resolve=resolve, builder=builder)

def traceback_package_module_path(package: str, *, header: bool = None, footer: bool = None, resolve: bool = False, builder: type[PurePath] = Path) -> str:
    traceback: str = traceback_package(package=package)
    return inspect_module_path(file=traceback, header=header, footer=footer, resolve=resolve, builder=builder)

@dataclass(kw_only=True)
class PathAPI:

    path: InitVar[Union[str, Path]] = field(init=True, repr=True)
    module: InitVar[Union[str, Path]] = field(default=None, init=True, repr=True)

    _path_ : Path = field(default=None, init=False, repr=False)
    _module_: Path = field(default=None, init=False, repr=False)

    def __post_init__(self, path: Union[str, Path], module: Union[str, Path] = None):
        if isinstance(path, str):
            self._path_ = inspect_file(path)
        else:
            self._path_ = path
        if module is None:
            self._module_: Path = traceback_current_module(resolve=True)
        elif isinstance(module, str):
            self._module_: Path = inspect_module(module, resolve=True)
        else:
            self._module_: Path = module

    @property
    def file(self) -> Path:
        return self._module_ / self._path_

    @property
    def exists(self) -> bool:
        return self.file.exists()

    def __repr__(self) -> str:
        return repr(inspect_path(self.file))