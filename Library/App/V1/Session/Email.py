from typing import Union
from dataclasses import dataclass, field

from Library.App.V1.Session.Storage import StorageAPI

@dataclass(kw_only=True)
class EmailAPI(StorageAPI):

    to: Union[str, list] = field(default=None, init=True, repr=True)
    cc: Union[str, list] = field(default=None, init=True, repr=True)
    bcc: Union[str, list] = field(default=None, init=True, repr=True)
    subject: Union[str, list] = field(default=None, init=True, repr=True)
    message: Union[str, list] = field(default=None, init=True, repr=True)