import secrets
from typing import Union

from Library.Credential.Credential import CredentialAPI
from Library.Credential.Type import CredentialType
from Library.Credential.Vault import VaultAPI
from Library.Database import PostgresDatabaseAPI

class SessionAPI:

    SERVICE: str = "Framework"
    NAME: str = "Session Key"
    KEY: str = "Key"

    _BYTES_: int = 32

    @classmethod
    def secret(cls, *, database: str = "Quant") -> Union[str, None]:
        vault = VaultAPI(database=database)
        try:
            with PostgresDatabaseAPI.attach(database=database) as db:
                if not db.exists(schema=CredentialAPI.Schema, table=CredentialAPI.Table): return None
            values = vault.internal(service=cls.SERVICE, name=cls.NAME)
            if values and values.get(cls.KEY): return values[cls.KEY].Value
            owner = vault.administrator()
            if owner is None: return None
            stored = vault.store(by=owner, Service=cls.SERVICE, Name=cls.NAME, Kind=CredentialType.ApiKey.name, Owner=owner,
                                   Username=CredentialAPI.pack(cls.SERVICE), Secret=CredentialAPI.pack({cls.KEY: secrets.token_hex(cls._BYTES_)}))
            return stored.secrets()[cls.KEY].Value
        except Exception as error:
            vault._log_.debug(lambda error=error: f"Session Key: Skipped · {error}")
            return None