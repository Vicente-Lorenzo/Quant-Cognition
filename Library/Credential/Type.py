from Library.Utility.Enumeration import EnumerationAPI

class CredentialType(EnumerationAPI):

    Password = 0
    Token = 1
    API = 2
    OAuth2 = 3
    Certificate = 4

class LayoutAPI:

    @staticmethod
    def layout(kind) -> tuple:
        match CredentialType.parse(kind):
            case CredentialType.Password: return ("Identifier",), ("Secret",)
            case CredentialType.Token: return ("Identifier",), ("Secret",)
            case CredentialType.API: return ("Identifier",), ("Secret", "Passphrase")
            case CredentialType.OAuth2: return ("Identifier", "Account"), ("Secret", "AccessToken", "RefreshToken")
            case CredentialType.Certificate: return ("Identifier",), ("Secret", "Passphrase")
            case _: return ("Identifier",), ("Secret",)

    @classmethod
    def identifiers(cls, kind) -> tuple:
        return cls.layout(kind)[0]

    @classmethod
    def secrets(cls, kind) -> tuple:
        return cls.layout(kind)[1]

    @classmethod
    def identifier(cls, kind) -> str:
        return cls.identifiers(kind)[0]

    @classmethod
    def secret(cls, kind) -> str:
        return cls.secrets(kind)[0]

    @classmethod
    def template(cls, kind, secret: bool = False) -> dict:
        return {name: "" for name in (cls.secrets(kind) if secret else cls.identifiers(kind))}