from typing import Union
# import mailer
# from mailer.report import Report
from dash import html

from Library.Utility.HTML import htmlize
from Library.Logging.Logging import VerboseLevel
from Library.Logging.Report import ReportLoggingAPI
from Library.Logging.Web import WebLoggingAPI

class EmailLoggingAPI(WebLoggingAPI, ReportLoggingAPI):

    _email_title_: str = None
    _email_from_address_: str = None
    _email_to_addresses_: Union[list[str], str] = None
    _email_cc_addresses_: Union[list[str], str] = None
    _email_default_address_ = "lisbon.eqd.exo.monitoring@bnpparibas.com"
    _email_download_hyperlink_: str = None

    @classmethod
    def _setup_class_(cls) -> None:
        super()._setup_class_()
        cls.set_verbose_level(VerboseLevel.Silent, default=True)
        # cls.set_email_from_address(from_address=cls._user_info_.email)
        cls.set_email_to_addresses(to_addresses=[cls._email_default_address_])
        # cls.set_email_cc_addresses(cc_addresses=[cls._user_info_.email])

    @classmethod
    def set_email_title(cls, title: str) -> None:
        with cls._class_lock_:
            if cls.is_entered(): return
            cls._email_title_ = title

    @classmethod
    def set_email_from_address(cls, from_address: str) -> None:
        with cls._class_lock_:
            if cls.is_entered(): return
            cls._email_from_address_ = from_address

    @classmethod
    def set_email_to_addresses(cls, to_addresses: Union[list[str], str]) -> None:
        with cls._class_lock_:
            if cls.is_entered(): return
            cls._email_to_addresses_ = to_addresses

    @classmethod
    def set_email_cc_addresses(cls, cc_addresses: Union[list[str], str]) -> None:
        with cls._class_lock_:
            if cls.is_entered(): return
            cls._email_cc_addresses_ = cc_addresses

    @classmethod
    def set_email_download_hyperlink(cls, download_hyperlink: str) -> None:
        with cls._class_lock_:
            if cls.is_entered(): return
            cls._email_download_hyperlink_ = download_hyperlink

    @classmethod
    def output(cls, verbose: VerboseLevel, log) -> None:
        super().output(verbose=verbose, log=log)

    @classmethod
    def _exit_(cls):
        if cls.is_success_report():
            result_tag = cls._SUCCESS_TAG_
            result_color = "green"
        elif cls.is_failure_report():
            result_tag = cls._FAILURE_TAG_
            result_color = "red"
        else: return

        if not cls._email_title_: return
        if not cls._email_from_address_: return
        if not cls._email_to_addresses_: return
        if not cls._email_cc_addresses_: return
        if not cls._email_download_hyperlink_: return

        threshold_tag = f"[Threshold = {cls._class_verbose_threshold_.name}]"
        execution_tag = f"[{cls._host_info_} - {cls._exec_info_} - {cls._path_info_}]"
        timestamp_tag = f"[{cls.timestamp()}]"
        time_tag = f"[{cls.class_timer.result()}]"
        title = " @ ".join([result_tag, execution_tag, timestamp_tag]) if not cls._email_title_ else cls._email_title_

        r = Report()
        r.append(htmlize(html.Div(result_tag, style={"color": result_color, "font-size": "10pt", "font-weight": "bold", "font-family": "Consolas"})))
        r.append(htmlize(html.Div(threshold_tag, style={"font-size": "10pt", "font-weight": "bold", "font-family": "Consolas"})))
        r.append(htmlize(html.Br()))
        r.append(htmlize(html.Div(execution_tag, style={"font-size": "10pt", "font-weight": "bold", "font-family": "Consolas"})))
        r.append(htmlize(html.Div(timestamp_tag, style={"font-size": "10pt", "font-weight": "bold", "font-family": "Consolas"})))
        r.append(htmlize(html.Div(time_tag, style={"font-size": "10pt", "font-weight": "bold", "font-family": "Consolas"})))
        r.append(htmlize(html.Div(html.A("Download Log (S3)", href=cls._email_download_hyperlink_, style={"font-size": "10pt", "font-weight": "bold", "font-family": "Consolas"}))))

        mailer.send(
            subject=title,
            from_=cls._email_from_address_,
            to=cls._email_to_addresses_,
            cc=cls._email_cc_addresses_,
            content=r.generate()
        )