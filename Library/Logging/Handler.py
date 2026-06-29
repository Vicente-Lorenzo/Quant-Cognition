import traceback
from io import BytesIO
from typing import Callable
from functools import wraps

from Library.Logging.Logging import VerboseLevel
from Library.Logging.Console import ConsoleLoggingAPI
from Library.Logging.File import FileLoggingAPI
from Library.Logging.Web import WebLoggingAPI
from Library.Logging.Email import EmailLoggingAPI

class HandlerLoggingAPI:

    def __init__(self, *args, **kwargs) -> None:
        self.console = ConsoleLoggingAPI(*args, **kwargs)
        self.file = FileLoggingAPI(*args, **kwargs)
        self.web = WebLoggingAPI(*args, **kwargs)
        self.email = EmailLoggingAPI(*args, **kwargs)

    def set_class_tags(self, *args, **kwargs) -> None:
        self.console.set_class_tags(*args, **kwargs)
        self.file.set_class_tags(*args, **kwargs)
        self.web.set_class_tags(*args, **kwargs)
        self.email.set_class_tags(*args, **kwargs)

    def set_instance_tags(self, *args, **kwargs) -> None:
        self.console.set_instance_tags(*args, **kwargs)
        self.file.set_instance_tags(*args, **kwargs)
        self.web.set_instance_tags(*args, **kwargs)
        self.email.set_instance_tags(*args, **kwargs)

    def set_verbose_level(self, verbose: VerboseLevel) -> None:
        self.console.set_verbose_level(verbose)
        self.file.set_verbose_level(verbose)
        self.web.set_verbose_level(verbose)
        self.email.set_verbose_level(verbose)

    def reset_verbose_level(self) -> None:
        self.console.reset_verbose_level()
        self.file.reset_verbose_level()
        self.web.reset_verbose_level()
        self.email.reset_verbose_level()

    def debug(self, content: Callable[[], str | BytesIO] | str) -> None:
        self.console.debug(content)
        self.file.debug(content)
        self.web.debug(content)
        self.email.debug(content)

    def info(self, content: Callable[[], str | BytesIO] | str) -> None:
        self.console.info(content)
        self.file.info(content)
        self.web.info(content)
        self.email.info(content)

    def alert(self, content: Callable[[], str | BytesIO] | str) -> None:
        self.console.alert(content)
        self.file.alert(content)
        self.web.alert(content)
        self.email.alert(content)

    def warning(self, content: Callable[[], str | BytesIO] | str) -> None:
        self.console.warning(content)
        self.file.warning(content)
        self.web.warning(content)
        self.email.warning(content)

    def error(self, content: Callable[[], str | BytesIO] | str) -> None:
        self.console.error(content)
        self.file.error(content)
        self.web.error(content)
        self.email.error(content)

    def exception(self, content: Callable[[], str | BytesIO] | str) -> None:
        self.console.exception(content)
        self.file.exception(content)
        self.web.exception(content)
        self.email.exception(content)

    def __enter__(self):
        self.console.__enter__()
        self.file.__enter__()
        self.web.__enter__()
        self.email.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.console.__exit__(exc_type, exc_value, exc_traceback)
        self.file.__exit__(exc_type, exc_value, exc_traceback)
        self.web.__exit__(exc_type, exc_value, exc_traceback)
        self.email.__exit__(exc_type, exc_value, exc_traceback)
        return self

    def guard(self, func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                self.__enter__()
                self.debug(lambda: f"Initiated @ {func.__name__}")
                return func(*args, **kwargs)
            except Exception as e:
                self.exception(lambda: f"Failed @ {func.__name__}")
                self.exception(lambda: ''.join(traceback.format_exception(e))[:-1])
                raise
            finally:
                self.debug(lambda: f"Terminated @ {func.__name__}")
                self.__exit__(None, None, None)
        return wrapper