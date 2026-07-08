from dataclasses import dataclass, field

from Library.App.V2.Session.Storage import StorageAPI
from Library.Utility.Typing import MISSING

@dataclass(kw_only=True)
class EmailAPI(StorageAPI):

    to: str | list = field(default=MISSING, init=True, repr=True)
    cc: str | list = field(default=MISSING, init=True, repr=True)
    bcc: str | list = field(default=MISSING, init=True, repr=True)
    subject: str | list = field(default=MISSING, init=True, repr=True)
    message: str | list = field(default=MISSING, init=True, repr=True)