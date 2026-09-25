import secrets
from typing import Union

from Library.Credential.Credential import CredentialAPI
from Library.Credential.Type import CredentialType, LayoutAPI
from Library.Credential.Vault import VaultAPI
from Library.Database import PostgresDatabaseAPI
from Library.Logging import LoggingAPI

class SessionAPI:

    @staticmethod
    def secret(*, database: str = "Quant") -> Union[str, None]:
        vault, key = VaultAPI(database=database), LayoutAPI.secret(CredentialType.Token)
        try:
            with PostgresDatabaseAPI.attach(database=database) as db:
                if not db.exists(schema=CredentialAPI.Schema, table=CredentialAPI.Table): return None
            values = vault.internal(service="Framework", name="Web Session")
            if values and values.get(key): return values[key].Value
            owner = vault.administrator()
            if owner is None: return None
            return vault.ensure(service="Framework", name="Web Session", secret=secrets.token_hex(32), by=owner, Kind=CredentialType.Token.name, Identifier=CredentialAPI.pack("Framework"), Owner=owner).secrets()[key].Value
        except Exception as error:
            LoggingAPI().warning(lambda error=error: f"Session Secret: Failed · {error}")
            return None