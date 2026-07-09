import os
import secrets

from Library.Auth.Auth import AuthAPI
from Library.Auth.Role import RoleAPI
from Library.Auth.User import UserAPI
from Library.Database import PostgresDatabaseAPI

def setup_auth(db):
    db.create(schema=AuthAPI.Schema)
    UserAPI(db=db, migrate=True, autosave=False, autoload=False)

def seed_admin(auth):
    username = os.environ.get("QUANT_ADMIN_USER", "admin")
    if auth.find(username) is not None:
        print(f"Admin '{username}' already exists")
        return
    password = os.environ.get("QUANT_ADMIN_PASSWORD") or secrets.token_urlsafe(16)
    auth.create(username=username, email=os.environ.get("QUANT_ADMIN_EMAIL"), name="Administrator", password=password, role=RoleAPI.Administrator, provider="Local")
    print(f"Admin '{username}' created")
    if "QUANT_ADMIN_PASSWORD" not in os.environ:
        print(f"Generated password: {password}")

def main():
    with PostgresDatabaseAPI(database="Quant") as db:
        setup_auth(db)
    seed_admin(AuthAPI(database="Quant"))

if __name__ == "__main__":
    main()