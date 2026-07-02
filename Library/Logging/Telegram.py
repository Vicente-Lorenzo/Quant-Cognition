import requests

from io import BytesIO
from typing import Union, Callable

from Library.Logging import VerboseLevel, LoggingAPI, TelegramConfigurationAPI
from Library.Database.Dataframe import pl

class TelegramAPI(LoggingAPI):

    _DEBUG_ICON: str = "⚙️"
    _INFO_ICON: str = "ℹ️"
    _ALERT_ICON: str = "🔔"
    _WARNING_ICON: str = "⚠️"
    _ERROR_ICON: str = "❌"
    _EXCEPTION_ICON: str = "🛑"

    _TIMESTAMP: str = "at {timestamp}"

    _LOG: TelegramConfigurationAPI = TelegramConfigurationAPI(Token="8183617727:AAGBFcbS104QXYczyB06UKA9StjCkK2RmRE", ChatID="-1002607268309")
    _LAB: TelegramConfigurationAPI = TelegramConfigurationAPI(Token="8032541880:AAFZEDPQPlVd6SVIcA7GohoiaK_-tNyW050", ChatID="-1002565200595")

    _GROUP: dict = {
        "Forex (Majors)": TelegramConfigurationAPI(Token="7180406910:AAG_JtWcwrFOdU0vrFo3u3YE60xJouCbDj8", ChatID="-1002557774416"),
        "Forex (Minors)": TelegramConfigurationAPI(Token="7858647408:AAH7M97_euohIMGX8X4gu3qtXbxKPBvHdHg", ChatID="-1002402990655"),
        "Forex (Exotics)": TelegramConfigurationAPI(Token="8020370305:AAF_XqDHIrp-QYkMT94DDjDd047SJZnQkvI", ChatID="-1002678006774"),
        "Stocks (US)": TelegramConfigurationAPI(Token="7621222262:AAHc1E-oQV7IFQhn8zecUU9awLhmYx72jc0", ChatID="-1002602965934"),
        "Stocks (EU)": TelegramConfigurationAPI(Token="7779184958:AAHnTVhELss3Oxy9wz8xgjoWl5--sU5BXp4", ChatID="-1002677954902"),
        "Metals": TelegramConfigurationAPI(Token="7955067039:AAFk26Be2Rip_IW26b-j0hpix1vJ3NWcAVM", ChatID="-1002683975427")}

    _MESSAGE_URL: str = "https://api.telegram.org/bot{0}/sendMessage?chat_id={1}"
    _DOCUMENT_URL: str = "https://api.telegram.org/bot{0}/sendDocument?chat_id={1}"

    _LOG_MESSAGE_URL: str = _MESSAGE_URL.format(_LOG.Token, _LOG.ChatID)
    _LOG_DOCUMENT_URL: str = _DOCUMENT_URL.format(_LOG.Token, _LOG.ChatID)

    _LAB_MESSAGE_URL: str = _MESSAGE_URL.format(_LAB.Token, _LAB.ChatID)
    _LAB_DOCUMENT_URL: str = _DOCUMENT_URL.format(_LAB.Token, _LAB.ChatID)

    _GROUP_MESSAGE_URL: Union[str, None] = None
    _GROUP_DOCUMENT_URL: Union[str, None] = None

    @classmethod
    def setup(cls, verbose: VerboseLevel, uid: str, **kwargs) -> None:
        super().setup(verbose, **kwargs)
        group = TelegramAPI._GROUP[uid]
        cls._GROUP_MESSAGE_URL = TelegramAPI._MESSAGE_URL.format(group.Token, group.ChatID)
        cls._GROUP_DOCUMENT_URL = TelegramAPI._DOCUMENT_URL.format(group.Token, group.ChatID)

    @staticmethod
    def _format_tag(static: str, tag: str) -> str:
        static += f"<code>{tag.center(27)}</code>\n"
        return static

    def _format_level(self, level: VerboseLevel, level_icon: str) -> str:
        level_name = f" {level.name} "
        top_hline = f"{level_icon} {level_name.center(22, "-")} {level_icon}"
        middle_line = "-" * 28
        bottom_hline = f"{level_icon} {"-" * 22} {level_icon}"
        static = (
            f"<code>{top_hline}</code>\n"
            "<pre>{content}</pre>\n"
            f"<code>{middle_line}\n</code>"
        )
        for base_tags in LoggingAPI._base_tags.values():
            static = TelegramAPI._format_tag(static, base_tags)
        for class_tags in TelegramAPI._class_tags.values():
            static = TelegramAPI._format_tag(static, class_tags)
        for instance_tags in self._instance_tags.values():
            static = TelegramAPI._format_tag(static, instance_tags)
        static += (
            f"<code>{middle_line}\n</code>"
            "<code>{timestamp}</code>\n"
            f"<code>{bottom_hline}</code>"
        )
        return static

    def _format(self) -> None:
        self._static_log_debug: str = self._format_level(VerboseLevel.Debug, TelegramAPI._DEBUG_ICON)
        self._static_log_info: str = self._format_level(VerboseLevel.Info, TelegramAPI._INFO_ICON)
        self._static_log_alert: str = self._format_level(VerboseLevel.Alert, TelegramAPI._ALERT_ICON)
        self._static_log_warning: str = self._format_level(VerboseLevel.Warning, TelegramAPI._WARNING_ICON)
        self._static_log_error: str = self._format_level(VerboseLevel.Error, TelegramAPI._ERROR_ICON)
        self._static_log_exception: str = self._format_level(VerboseLevel.Exception, TelegramAPI._EXCEPTION_ICON)

    @staticmethod
    def _build_log(message_url: str, document_url: str, static_log: str, content_func: Callable[[], str | BytesIO]):
        content = content_func()
        timestamp = TelegramAPI._TIMESTAMP.format(timestamp=LoggingAPI.timestamp())
        data = {"parse_mode": "html"}
        if isinstance(content, BytesIO):
            data["caption"] = timestamp
            files = {"document": ("image.png", content, "image/png")}
            return document_url, data, files
        else:
            data["text"] = static_log.format(content=content, timestamp=timestamp)
            return message_url, data, None

    @staticmethod
    def _output_log(message_url: str, document_url: str, static_log: str, content_func: Callable[[], str | BytesIO]):
        url, data, files = TelegramAPI._build_log(message_url, document_url, static_log, content_func)
        return requests.post(url, data=data, files=files)

    def _debug(self, content_func: Callable[[], str | BytesIO]):
        self._log(self._LAB_MESSAGE_URL, self._LAB_DOCUMENT_URL, self._static_log_debug, content_func)

    def _info(self, content_func: Callable[[], str | BytesIO]):
        self._log(self._LAB_MESSAGE_URL, self._LAB_DOCUMENT_URL, self._static_log_info, content_func)

    def _alert(self, content_func: Callable[[], str | BytesIO]):
        self._log(self._GROUP_MESSAGE_URL, self._GROUP_DOCUMENT_URL, self._static_log_alert, content_func)

    def _warning(self, content_func: Callable[[], str | BytesIO]):
        self._log(self._LOG_MESSAGE_URL, self._LOG_DOCUMENT_URL, self._static_log_warning, content_func)

    def _error(self, content_func: Callable[[], str | BytesIO]):
        self._log(self._LOG_MESSAGE_URL, self._LOG_DOCUMENT_URL, self._static_log_error, content_func)

    def _exception(self, content_func: Callable[[], str | BytesIO]):
        self._log(self._LOG_MESSAGE_URL, self._LOG_DOCUMENT_URL, self._static_log_exception, content_func)