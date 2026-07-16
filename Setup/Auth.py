import sys
import secrets
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Library.Auth.Auth import AuthAPI
from Library.Auth.Role import RoleAPI
from Library.Auth.Team import TeamAPI
from Library.Auth.Office import OfficeAPI
from Library.Auth.User import UserAPI
from Library.Database import PostgresDatabaseAPI
from Library.Logging import HandlerLoggingAPI

ADMIN = "vicente.aser.lorenzo@gmail.com"

def setup_auth(db):
    db.create(schema=AuthAPI.Schema)
    TeamAPI(db=db, migrate=True, autosave=False, autoload=False)
    OfficeAPI(db=db, migrate=True, autosave=False, autoload=False)
    UserAPI(db=db, migrate=True, autosave=False, autoload=False)

def seed_admin(auth, *, username=ADMIN, email=ADMIN, name="Vicente Lorenzo", password=None):
    if auth.find(username) is not None: return None
    secret = password or secrets.token_urlsafe(16)
    auth.create(username=username, email=email, name=name, password=secret, role=RoleAPI.Administrator, provider="Local")
    return secret

def main(database="Quant"):
    with HandlerLoggingAPI(Class="Setup", Subclass="Auth") as log:
        try:
            with PostgresDatabaseAPI(database=database) as db:
                setup_auth(db)
            secret = seed_admin(AuthAPI(database=database))
            detail = f"Admin Created · Password {secret}" if secret is not None else "Admin Present"
            log.info(lambda: f"Auth Setup: Completed · Schema + 3 Tables · {detail}")
            return 0
        except Exception as error:
            log.exception(lambda: f"Auth Setup: Failed · Due to {error}")
            return 1

if __name__ == "__main__":
    raise SystemExit(main())