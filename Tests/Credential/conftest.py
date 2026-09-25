import pytest

from Library.Auth import AuthAPI, RoleAPI, UserAPI
from Library.Credential import CredentialAPI, VaultAPI
from Library.Database.Postgres.Postgres import PostgresDatabaseAPI
from Library.Database.Query import QueryAPI
from Script.Setup.Auth import setup_auth
from Script.Setup.Credential import setup_credential

@pytest.fixture(scope="module")
def vault():
    previous = {UserAPI: UserAPI.Database, CredentialAPI: CredentialAPI.Database}
    for cls in previous: cls.Database = "Tests"
    admin = PostgresDatabaseAPI(admin=True)
    try:
        admin.connect()
        if not admin.exists(database="Tests"): admin.create(database="Tests")
    finally:
        admin.disconnect()
    with PostgresDatabaseAPI(database="Tests") as db:
        db.executeone(QueryAPI('DROP SCHEMA IF EXISTS "Credential" CASCADE'))
        setup_auth(db)
        setup_credential(db)
    auth = AuthAPI(database="Tests")
    for username, role in (("admin@test.com", RoleAPI.Administrator), ("moderator@test.com", RoleAPI.Moderator), ("editor@test.com", RoleAPI.Editor), ("viewer@test.com", RoleAPI.Viewer), ("other@test.com", RoleAPI.Viewer)):
        if auth.find(username) is None: auth.create(username=username, email=username, name=username, password="secret", role=role)
    yield VaultAPI(database="Tests")
    for cls, database in previous.items(): cls.Database = database