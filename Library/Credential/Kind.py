from Library.Utility.Enumeration import EnumerationAPI

class CredentialKind(EnumerationAPI):

    Password = 0
    ApiKey = 1
    OAuth2 = 2
    Certificate = 3

class LayoutAPI:

    _LAYOUTS_ = {
        CredentialKind.Password: (("Username",), ("Password",)),
        CredentialKind.ApiKey: (("Identifier",), ("Key",)),
        CredentialKind.OAuth2: (("ClientId", "AccountId"), ("ClientSecret", "AccessToken", "RefreshToken")),
        CredentialKind.Certificate: (("Subject",), ("PrivateKey", "Passphrase"))
    }

    @classmethod
    def layout(cls, kind) -> tuple:
        return cls._LAYOUTS_.get(CredentialKind.parse(kind), (("Username",), ("Secret",)))

    @classmethod
    def usernames(cls, kind) -> tuple:
        return cls.layout(kind)[0]

    @classmethod
    def secrets(cls, kind) -> tuple:
        return cls.layout(kind)[1]

    @classmethod
    def username(cls, kind) -> str:
        return cls.usernames(kind)[0]

    @classmethod
    def secret(cls, kind) -> str:
        return cls.secrets(kind)[0]

    @classmethod
    def template(cls, kind, secret: bool = False) -> dict:
        return {name: "" for name in (cls.secrets(kind) if secret else cls.usernames(kind))}