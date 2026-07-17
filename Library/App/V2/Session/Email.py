from dataclasses import dataclass, field

from Library.App.V2.Session.State import StateAPI
from Library.Utility.Typing import MISSING

@dataclass(kw_only=True)
class EmailAPI(StateAPI):

    to: str | list = field(default=MISSING)
    cc: str | list = field(default=MISSING)
    bcc: str | list = field(default=MISSING)
    subject: str | list = field(default=MISSING)
    message: str | list = field(default=MISSING)