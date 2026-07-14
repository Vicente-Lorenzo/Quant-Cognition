import pytest

from Library.Auth import AuthAPI, RoleAPI, PasswordAPI, UserAPI, IdentityAPI, AnonymousAPI
from Library.Database.Postgres.Postgres import PostgresDatabaseAPI
from Library.Database.Query import QueryAPI
from Setup.Auth import setup_auth

DATABASE = "Tests"

@pytest.fixture(scope="module")
def auth():
    UserAPI.Database = DATABASE
    admin = PostgresDatabaseAPI(admin=True)
    try:
        admin.connect()
        if not admin.exists(database=DATABASE): admin.create(database=DATABASE)
    finally:
        admin.disconnect()
    with PostgresDatabaseAPI(database=DATABASE) as db:
        db.executeone(QueryAPI('DROP SCHEMA IF EXISTS "Auth" CASCADE'))
        setup_auth(db)
    return AuthAPI(database=DATABASE)

def test_role_hierarchy():
    assert RoleAPI.Administrator.grants(RoleAPI.Editor)
    assert RoleAPI.Editor.grants(RoleAPI.Viewer)
    assert not RoleAPI.Viewer.grants(RoleAPI.Editor)
    assert RoleAPI.Public.grants(RoleAPI.Public)
    assert RoleAPI.Editor.grants("Viewer")
    assert RoleAPI.Administrator.grants(1)
    assert RoleAPI.Administrator.grants(RoleAPI.Moderator)
    assert RoleAPI.Moderator.grants(RoleAPI.Editor)
    assert not RoleAPI.Moderator.grants(RoleAPI.Administrator)
    assert not RoleAPI.Editor.grants(RoleAPI.Moderator)

def test_password_roundtrip():
    digest = PasswordAPI.hash("Sup3r$ecret!")
    assert PasswordAPI.verify(digest, "Sup3r$ecret!")
    assert not PasswordAPI.verify(digest, "wrong")
    assert not PasswordAPI.verify("garbage", "x")
    assert not PasswordAPI.stale(digest)

def test_schema_created(auth):
    with PostgresDatabaseAPI(database=DATABASE) as db:
        frame = db.select(schema="Auth", table="User", limit=0, legacy=False)
    assert {"UID", "Email", "Password", "Role", "Active"}.issubset(set(frame.columns))

def test_create_and_find(auth):
    auth.create(username="editor", email="editor@x.com", name="Editor", password="pw12345678", role=RoleAPI.Editor)
    user = auth.find("editor")
    assert user is not None and user.UID == "editor"
    assert user.authority() is RoleAPI.Editor
    assert user.Password and user.Password != "pw12345678"
    assert auth.locate("editor@x.com") is not None

def test_authenticate(auth):
    auth.create(username="viewer", email="viewer@x.com", password="pw12345678", role=RoleAPI.Viewer)
    identity = auth.authenticate(username="viewer", password="pw12345678")
    assert isinstance(identity, IdentityAPI) and identity.get_id() == "viewer"
    assert identity.Role is RoleAPI.Viewer
    assert identity.grants(RoleAPI.Public)
    assert not identity.grants(RoleAPI.Editor)
    assert auth.authenticate(username="viewer", password="bad") is None
    assert auth.authenticate(username="ghost", password="x") is None

def test_provision_jit(auth):
    first = auth.provision(email="sso@x.com", provider="Cloudflare")
    second = auth.provision(email="sso@x.com", provider="Cloudflare")
    assert first is not None and first.UID == "sso@x.com"
    assert first.authority() is RoleAPI.Viewer and not first.Password
    assert second.UID == first.UID
    with PostgresDatabaseAPI(database=DATABASE) as db:
        rows = db.select(schema="Auth", table="User", condition='"Email" = :e:', parameters={"e": "sso@x.com"}, legacy=False)
    assert rows.height == 1

def test_anonymous_identity():
    anon = AnonymousAPI()
    assert anon.is_authenticated is False
    assert anon.grants(RoleAPI.Public)
    assert not anon.grants(RoleAPI.Viewer)
    assert anon.Role is RoleAPI.Public