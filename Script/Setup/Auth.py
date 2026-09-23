import sys
import secrets
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from Library.Auth.Auth import AuthAPI
from Library.Auth.Role import RoleAPI
from Library.Auth.Team import TeamAPI
from Library.Auth.Office import OfficeAPI
from Library.Auth.User import UserAPI
from Library.Credential import CredentialAPI, CredentialKind, CredentialManagerAPI
from Library.Database import PostgresDatabaseAPI
from Library.Logging import LoggingAPI
from Script.Setup.Credential import setup_credential
from Script.Task import attempt, migrate

ADMIN = "vicente.aser.lorenzo@gmail.com"

def setup_auth(db):
    db.create(schema=AuthAPI.Schema)
    migrate(db, TeamAPI, OfficeAPI, UserAPI)

def seed_admin(auth, *, username=ADMIN, email=ADMIN, name="Vicente Lorenzo", password=None):
    if auth.find(username) is not None: return None
    secret = password or secrets.token_urlsafe(16)
    auth.create(username=username, email=email, name=name, password=secret, role=RoleAPI.Administrator, provider="Local")
    return secret

def store_admin(secret, *, database="Quant", username=ADMIN):
    with PostgresDatabaseAPI(database=database) as db:
        setup_credential(db)
    manager = CredentialManagerAPI(database=database)
    manager.ensure(service="Framework", name="Administrator", secret={"Password": secret}, by=username, Kind=CredentialKind.Password.name, Username=CredentialAPI.pack(username), Owner=username)
    return f"{CredentialAPI.Schema} Framework · Administrator"

def install_auth(database="Quant"):
    with PostgresDatabaseAPI(database=database) as db:
        setup_auth(db)
    secret = seed_admin(AuthAPI(database=database))
    if secret is None: return "Schema + 3 Tables · Admin Present"
    return f"Schema + 3 Tables · Admin Created · Password In {store_admin(secret, database=database)}"

def main(database="Quant"):
    with LoggingAPI() as log:
        return attempt(log, "Auth", lambda: install_auth(database))

if __name__ == "__main__":
    raise SystemExit(main())