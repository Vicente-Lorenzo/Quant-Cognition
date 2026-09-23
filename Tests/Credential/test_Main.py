import pytest

from Library.Auth import AuthAPI, RoleAPI, UserAPI
from Library.Credential import CredentialAPI, CredentialManagerAPI
from Library.Database.Postgres.Postgres import PostgresDatabaseAPI
from Library.Database.Query import QueryAPI
from Library.Credential import Main
from Script.Setup.Auth import setup_auth
from Script.Setup.Credential import setup_credential

DATABASE = "Tests"

ADMIN = "admin@test.com"
EDITOR = "editor@test.com"
VIEWER = "viewer@test.com"

@pytest.fixture(scope="module")
def manager():
    for cls in (UserAPI, CredentialAPI): cls.Database = DATABASE
    admin = PostgresDatabaseAPI(admin=True)
    try:
        admin.connect()
        if not admin.exists(database=DATABASE): admin.create(database=DATABASE)
    finally:
        admin.disconnect()
    with PostgresDatabaseAPI(database=DATABASE) as db:
        db.executeone(QueryAPI('DROP SCHEMA IF EXISTS "Credential" CASCADE'))
        setup_auth(db)
        setup_credential(db)
    auth = AuthAPI(database=DATABASE)
    for username, role in ((ADMIN, RoleAPI.Administrator), (EDITOR, RoleAPI.Editor), (VIEWER, RoleAPI.Viewer)):
        if auth.find(username) is None: auth.create(username=username, email=username, name=username, password="secret", role=role)
    return CredentialManagerAPI(database=DATABASE)

@pytest.fixture
def clean(manager):
    yield
    for row in sorted(manager._select_(), key=lambda row: row.get("Parent") is None): manager.delete(row["UID"], by=ADMIN)

def cli(capsys, user: str, *arguments) -> tuple:
    code = Main.main(["--database", DATABASE, "--user", user, *arguments])
    return code, capsys.readouterr().out

def typed(monkeypatch, **values):
    monkeypatch.setattr(Main.getpass, "getpass", lambda prompt: values.get(prompt.split(" ")[0], ""))

def test_a_secret_is_prompted_never_passed(manager, clean, capsys, monkeypatch):
    with pytest.raises(SystemExit):
        Main.main(["--database", DATABASE, "store", "--service", "Spotware", "--name", "Demo", "--secret", "hunter2"])
    typed(monkeypatch, ClientSecret="cs", AccessToken="at")
    code, output = cli(capsys, EDITOR, "store", "--service", "Spotware", "--name", "Demo", "--kind", "OAuth2", "--username", '{"ClientId": "cid"}', "--secret", "--view-role", "Viewer", "--edit-role", "Editor")
    assert code == 0 and "stored" in output
    row = manager._select_(Service="Spotware", Name="Demo")[0]
    assert row["Owner"] == EDITOR and CredentialAPI.unpack(row["Secret"]) == {"ClientSecret": "cs", "AccessToken": "at"}

def test_listing_masks_and_carries_access(manager, clean, capsys, monkeypatch):
    typed(monkeypatch, Password="hunter2")
    cli(capsys, EDITOR, "store", "--service", "Framework", "--name", "Shared", "--secret", "--view-role", "Viewer", "--edit-role", "Editor")
    code, output = cli(capsys, VIEWER, "list")
    assert code == 0 and "Shared" in output and "hunter2" not in output and "***" in output and "View" in output
    code, output = cli(capsys, VIEWER, "show", "--service", "Framework", "--name", "Shared")
    assert code == 0 and "Access: View" in output and "hunter2" not in output

def test_reveal_needs_edit(manager, clean, capsys, monkeypatch):
    typed(monkeypatch, Password="hunter2")
    cli(capsys, EDITOR, "store", "--service", "Framework", "--name", "Shared", "--secret", "--view-role", "Viewer", "--edit-role", "Editor")
    code, output = cli(capsys, VIEWER, "reveal", "--service", "Framework", "--name", "Shared")
    assert code == 1 and "Rejected ·" in output and "hunter2" not in output
    code, output = cli(capsys, EDITOR, "reveal", "--service", "Framework", "--name", "Shared")
    assert code == 0 and "Password: hunter2" in output

def test_update_merges_the_prompted_keys_and_renames(manager, clean, capsys, monkeypatch):
    typed(monkeypatch, ClientSecret="cs", AccessToken="at", RefreshToken="rt")
    cli(capsys, ADMIN, "store", "--service", "Spotware", "--name", "Demo", "--kind", "OAuth2", "--secret")
    typed(monkeypatch, AccessToken="new")
    code, output = cli(capsys, ADMIN, "update", "--service", "Spotware", "--name", "Demo", "--secret", "--rename", "Live", "--expires", "2026-12-31 00:00:00")
    assert code == 0 and "updated" in output
    row = manager._select_(Service="Spotware", Name="Live")[0]
    assert CredentialAPI.unpack(row["Secret"]) == {"ClientSecret": "cs", "AccessToken": "new", "RefreshToken": "rt"}
    assert row["ExpiresAt"].year == 2026

def test_transfer_and_delete(manager, clean, capsys, monkeypatch):
    typed(monkeypatch, Password="x")
    cli(capsys, EDITOR, "store", "--service", "Framework", "--name", "Mine", "--secret")
    code, output = cli(capsys, VIEWER, "transfer", "--service", "Framework", "--name", "Mine", "--to", VIEWER)
    assert code == 1 and "Rejected ·" in output
    code, output = cli(capsys, EDITOR, "transfer", "--service", "Framework", "--name", "Mine", "--to", VIEWER)
    assert code == 0 and manager._select_(Name="Mine")[0]["Owner"] == VIEWER
    code, output = cli(capsys, VIEWER, "delete", "--service", "Framework", "--name", "Mine")
    assert code == 0 and manager._select_(Name="Mine") == []

def test_due_lists_only_what_the_reader_may_see(manager, clean, capsys, monkeypatch):
    typed(monkeypatch, Password="x")
    cli(capsys, ADMIN, "store", "--service", "Framework", "--name", "Private", "--secret", "--expires", "2000-01-01 00:00:00")
    cli(capsys, ADMIN, "store", "--service", "Framework", "--name", "Open", "--secret", "--expires", "2000-01-01 00:00:00", "--view-role", "Viewer", "--edit-role", "Viewer")
    code, output = cli(capsys, VIEWER, "due")
    assert code == 0 and "Open" in output and "Private" not in output and "x " not in output.split("\n", 1)[1]

def test_a_missing_target_is_rejected(manager, clean, capsys):
    code, output = cli(capsys, ADMIN, "show", "--service", "Framework", "--name", "Nothing")
    assert code == 1 and "not found" in output
    code, output = cli(capsys, ADMIN, "show")
    assert code == 1 and "--uid" in output

def test_no_user_acts_as_the_administrator(manager, clean, capsys, monkeypatch):
    typed(monkeypatch, Password="x")
    code = Main.main(["--database", DATABASE, "store", "--service", "Framework", "--name", "Defaulted", "--secret"])
    capsys.readouterr()
    administrator = manager.administrator()
    assert code == 0 and administrator is not None and manager._select_(Name="Defaulted")[0]["Owner"] == administrator