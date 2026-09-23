import pytest

from datetime import datetime, timedelta

from Library.Auth import AuthAPI, RoleAPI, UserAPI
from Library.Credential import CredentialAPI, Validity, CredentialType, VaultAPI, LayoutAPI, SecretAPI
from Library.Database.Postgres.Postgres import PostgresDatabaseAPI
from Library.Database.Query import QueryAPI
from Library.Utility.Datetime import utc_now
from Script.Setup.Auth import setup_auth
from Script.Setup.Credential import setup_credential

DATABASE = "Tests"

ADMIN = "admin@test.com"
MODERATOR = "moderator@test.com"
EDITOR = "editor@test.com"
VIEWER = "viewer@test.com"
OTHER = "other@test.com"

@pytest.fixture(scope="module")
def vault():
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
    for username, role in ((ADMIN, RoleAPI.Administrator), (MODERATOR, RoleAPI.Moderator), (EDITOR, RoleAPI.Editor), (VIEWER, RoleAPI.Viewer), (OTHER, RoleAPI.Viewer)):
        if auth.find(username) is None: auth.create(username=username, email=username, name=username, password="secret", role=role)
    return VaultAPI(database=DATABASE)

@pytest.fixture
def stored(vault):
    yield
    for row in sorted(vault._select_(), key=lambda row: row.get("Parent") is None):
        vault.delete(row["UID"], by=ADMIN)

def test_a_credential_defaults_to_owner_only(vault, stored):
    credential = vault.store(by=EDITOR, Service="Framework", Name="Default", Secret=CredentialAPI.pack("x"))
    assert credential.ViewRole is None and credential.EditRole is None
    assert vault.credentials(by=MODERATOR) == []
    assert [row["Name"] for row in vault.credentials(by=EDITOR)] == ["Default"]

def test_a_single_value_and_a_multi_value_credential_round_trip(vault, stored):
    single = vault.store(by=ADMIN, Service="Framework", Name="Single", Kind=CredentialType.Password.name, Username=CredentialAPI.pack("vicente"), Secret=CredentialAPI.pack("hunter2"))
    many = vault.store(by=ADMIN, Service="Spotware", Name="Many", Kind=CredentialType.OAuth2.name,
                         Username=CredentialAPI.pack({"ClientId": "cid", "AccountId": "42"}),
                         Secret=CredentialAPI.pack({"ClientSecret": "cs", "AccessToken": "at"}))
    assert vault.resolve(uid=single.UID, by=ADMIN)["Username"] == "vicente"
    assert vault.resolve(uid=single.UID, by=ADMIN)["Password"].Value == "hunter2"
    values = vault.resolve(uid=many.UID, by=ADMIN)
    assert values["ClientId"] == "cid" and values["AccountId"] == "42"
    assert values["ClientSecret"].Value == "cs" and values["AccessToken"].Value == "at"

def test_a_child_inherits_its_parent(vault, stored):
    parent = vault.store(by=ADMIN, Service="Spotware", Name="Application", Kind=CredentialType.OAuth2.name,
                           Username=CredentialAPI.pack({"ClientId": "cid"}), Secret=CredentialAPI.pack({"ClientSecret": "cs"}))
    child = vault.store(by=ADMIN, Service="Spotware", Name="Demo EUR", Kind=CredentialType.OAuth2.name, Parent=parent.UID,
                          Username=CredentialAPI.pack({"AccountId": "42"}), Secret=CredentialAPI.pack({"AccessToken": "at"}))
    values = vault.resolve(uid=child.UID, by=ADMIN)
    assert values["ClientId"] == "cid" and values["AccountId"] == "42"
    assert values["ClientSecret"].Value == "cs" and values["AccessToken"].Value == "at"

def test_a_secret_never_prints_itself(vault, stored):
    credential = vault.store(by=ADMIN, Service="Framework", Name="Masked", Secret=CredentialAPI.pack("hunter2"))
    secret = vault.resolve(uid=credential.UID, by=ADMIN)["Password"]
    assert str(secret) == SecretAPI.MASK and repr(secret) == SecretAPI.MASK
    assert f"{secret}" == SecretAPI.MASK and secret.Value == "hunter2"

def test_the_grid_never_carries_a_plaintext_secret(vault, stored):
    vault.store(by=ADMIN, Service="Framework", Name="Masked", Secret=CredentialAPI.pack({"Password": "hunter2"}))
    rows = vault.credentials(by=ADMIN)
    assert rows and "hunter2" not in rows[0]["Secret"]
    assert CredentialAPI.unpack(rows[0]["Secret"]) == {"Password": SecretAPI.MASK}

def test_public_is_refused_as_a_threshold(vault, stored):
    with pytest.raises(ValueError, match="cannot be Public"):
        vault.store(by=ADMIN, Service="Framework", Name="Public", ViewRole=RoleAPI.Public.name, EditRole=RoleAPI.Public.name)

def test_a_threshold_may_not_exceed_the_setter_role(vault, stored):
    with pytest.raises(ValueError, match="above your own role"):
        vault.store(by=EDITOR, Service="Framework", Name="Too High", ViewRole=RoleAPI.Moderator.name, EditRole=RoleAPI.Moderator.name)

def test_edit_may_not_be_below_view(vault, stored):
    with pytest.raises(ValueError, match="below ViewRole"):
        vault.store(by=ADMIN, Service="Framework", Name="Inverted", ViewRole=RoleAPI.Moderator.name, EditRole=RoleAPI.Editor.name)

def test_an_owner_only_credential_takes_no_edit_role(vault, stored):
    with pytest.raises(ValueError, match="owner only"):
        vault.store(by=VIEWER, Service="Framework", Name="Private", ViewRole=None, EditRole=RoleAPI.Viewer.name)

def test_owner_only_hides_the_row_from_every_other_role(vault, stored):
    vault.store(by=VIEWER, Service="Framework", Name="Private", ViewRole=None, EditRole=None, Secret=CredentialAPI.pack("x"))
    assert [row["Name"] for row in vault.credentials(by=VIEWER)] == ["Private"]
    assert vault.credentials(by=OTHER) == []
    assert vault.credentials(by=MODERATOR) == []
    assert [row["Name"] for row in vault.credentials(by=ADMIN)] == ["Private"]

def test_view_lets_a_viewer_use_but_never_reveal(vault, stored):
    credential = vault.store(by=EDITOR, Service="Framework", Name="Shared", ViewRole=RoleAPI.Viewer.name, EditRole=RoleAPI.Editor.name, Secret=CredentialAPI.pack("hunter2"))
    assert vault.resolve(uid=credential.UID, by=VIEWER)["Password"].Value == "hunter2"
    assert vault.reveal(credential.UID, by=VIEWER) is None
    assert vault.update(credential.UID, by=VIEWER, Name="Renamed") is None
    assert vault.delete(credential.UID, by=VIEWER) is False
    assert vault.reveal(credential.UID, by=EDITOR) == {"Password": "hunter2"}

def test_an_owner_keeps_access_whatever_the_thresholds_say(vault, stored):
    credential = vault.store(by=VIEWER, Service="Framework", Name="Owned", ViewRole=None, EditRole=None, Secret=CredentialAPI.pack("x"))
    assert vault.reveal(credential.UID, by=VIEWER) == {"Password": "x"}
    assert vault.update(credential.UID, by=VIEWER, Name="Still Owned") is not None

def test_an_administrator_reaches_everything(vault, stored):
    credential = vault.store(by=VIEWER, Service="Framework", Name="Owned", ViewRole=None, EditRole=None, Secret=CredentialAPI.pack("x"))
    assert vault.reveal(credential.UID, by=ADMIN) == {"Password": "x"}
    assert vault.update(credential.UID, by=ADMIN, Name="Adopted") is not None

def test_resolving_stamps_used_at_and_used_by(vault, stored):
    credential = vault.store(by=ADMIN, Service="Framework", Name="Stamped", ViewRole=RoleAPI.Editor.name, EditRole=RoleAPI.Editor.name, Secret=CredentialAPI.pack("x"))
    assert vault.credential(credential.UID, by=ADMIN)["UsedAt"] is None
    vault.resolve(uid=credential.UID, by=EDITOR)
    row = vault.credential(credential.UID, by=ADMIN)
    assert row["UsedBy"] == EDITOR and row["UsedAt"] is not None

def test_only_expiring_credentials_come_back_as_due(vault, stored):
    vault.store(by=ADMIN, Service="Framework", Name="Never", Secret=CredentialAPI.pack("x"))
    soon = vault.store(by=ADMIN, Service="Framework", Name="Soon", Secret=CredentialAPI.pack("x"), ExpiresAt=utc_now() + timedelta(hours=1))
    vault.store(by=ADMIN, Service="Framework", Name="Later", Secret=CredentialAPI.pack("x"), ExpiresAt=utc_now() + timedelta(days=30))
    due = [row["UID"] for row in vault.due(margin=86400)]
    assert due == [soon.UID]

def test_refresh_rotates_only_the_supplied_keys(vault, stored):
    credential = vault.store(by=ADMIN, Service="Spotware", Name="Rotating", Kind=CredentialType.OAuth2.name,
                               Secret=CredentialAPI.pack({"ClientSecret": "cs", "AccessToken": "old", "RefreshToken": "rt"}),
                               ExpiresAt=utc_now() + timedelta(hours=1))
    expires = utc_now() + timedelta(days=30)
    vault.refresh(credential.UID, {"AccessToken": "new"}, expires=expires, by=ADMIN)
    values = vault.reveal(credential.UID, by=ADMIN)
    assert values == {"ClientSecret": "cs", "AccessToken": "new", "RefreshToken": "rt"}
    assert vault.credential(credential.UID, by=ADMIN)["ExpiresAt"].date() == expires.date()

def test_transfer_moves_the_owner(vault, stored):
    credential = vault.store(by=ADMIN, Service="Framework", Name="Handover", ViewRole=RoleAPI.Editor.name, EditRole=RoleAPI.Editor.name)
    assert vault.transfer(credential.UID, EDITOR, by=ADMIN) is True
    assert vault.credential(credential.UID, by=ADMIN)["Owner"] == EDITOR

def test_the_kind_declares_which_keys_are_secret():
    assert LayoutAPI.usernames(CredentialType.OAuth2) == ("ClientId", "AccountId")
    assert LayoutAPI.secrets(CredentialType.OAuth2) == ("ClientSecret", "AccessToken", "RefreshToken")
    assert LayoutAPI.username(CredentialType.Password) == "Username"
    assert LayoutAPI.secret(CredentialType.Password) == "Password"

def test_the_column_order_is_the_declared_one(vault):
    declared = list(CredentialAPI().Structure)
    assert declared[:8] == ["UID", "Service", "Name", "Kind", "Username", "Secret", "Fields", "ExpiresAt"]
    assert declared[8:12] == ["Parent", "Owner", "ViewRole", "EditRole"]
    assert declared[12:] == ["UsedAt", "UsedBy", "UpdatedAt", "UpdatedBy"]

def test_the_session_key_survives_a_restart(vault, stored):
    from Library.Credential import SessionAPI
    first = SessionAPI.secret(database=DATABASE)
    second = SessionAPI.secret(database=DATABASE)
    assert first and first == second and len(first) == 64

def test_only_a_known_user_may_store(vault, stored):
    with pytest.raises(PermissionError, match="signed-in user"):
        vault.store(by=None, Service="Framework", Name="Nobody", Secret=CredentialAPI.pack("x"))
    with pytest.raises(PermissionError, match="signed-in user"):
        vault.store(by="stranger@test.com", Service="Framework", Name="Stranger", Secret=CredentialAPI.pack("x"))

def test_a_non_administrator_may_only_own_what_they_store(vault, stored):
    with pytest.raises(PermissionError, match="may only own what they create"):
        vault.store(by=EDITOR, Service="Framework", Name="Planted", Owner=VIEWER, Secret=CredentialAPI.pack("x"))
    assert vault.store(by=ADMIN, Service="Framework", Name="Assigned", Owner=VIEWER, Secret=CredentialAPI.pack("x")).Owner == VIEWER

def test_service_and_name_are_unique(vault, stored):
    first = vault.store(by=ADMIN, Service="Spotware", Name="Demo", Secret=CredentialAPI.pack("x"))
    with pytest.raises(ValueError, match="already exists"):
        vault.store(by=EDITOR, Service="Spotware", Name="Demo", Secret=CredentialAPI.pack("y"))
    other = vault.store(by=ADMIN, Service="Spotware", Name="Live", Secret=CredentialAPI.pack("z"))
    with pytest.raises(ValueError, match="already exists"):
        vault.update(other.UID, by=ADMIN, Name="Demo")
    assert vault.update(first.UID, by=ADMIN, Name="Demo", Fields=CredentialAPI.pack({"Host": "demo"})) is not None

def test_the_database_enforces_uniqueness_too(vault, stored):
    vault.store(by=ADMIN, Service="Spotware", Name="Demo", Secret=CredentialAPI.pack("x"))
    with PostgresDatabaseAPI(database=DATABASE) as db:
        with pytest.raises(Exception):
            db.executeone(QueryAPI('INSERT INTO "Credential"."Credential" ("UID", "Service", "Name", "Kind") VALUES (\'duplicate\', \'Spotware\', \'Demo\', \'Password\')'))

def test_a_parent_must_exist_and_stay_one_level(vault, stored):
    with pytest.raises(ValueError, match="does not exist"):
        vault.store(by=ADMIN, Service="Spotware", Name="Orphan", Parent="missing")
    parent = vault.store(by=ADMIN, Service="Spotware", Name="Application")
    child = vault.store(by=ADMIN, Service="Spotware", Name="Account", Parent=parent.UID)
    with pytest.raises(ValueError, match="own parent"):
        vault.update(parent.UID, by=ADMIN, Parent=parent.UID)
    with pytest.raises(ValueError, match="cannot itself inherit"):
        vault.store(by=ADMIN, Service="Spotware", Name="Grandchild", Parent=child.UID)
    other = vault.store(by=ADMIN, Service="Spotware", Name="Other")
    with pytest.raises(ValueError, match="others inherit from"):
        vault.update(parent.UID, by=ADMIN, Parent=other.UID)

def test_a_parent_must_be_visible_to_whoever_links_it(vault, stored):
    hidden = vault.store(by=ADMIN, Service="Spotware", Name="Application", Secret=CredentialAPI.pack({"ClientSecret": "cs"}))
    with pytest.raises(PermissionError, match="parent credential"):
        vault.store(by=EDITOR, Service="Spotware", Name="Account", Parent=hidden.UID)

def test_resolving_a_child_needs_sight_of_its_parent(vault, stored):
    parent = vault.store(by=EDITOR, Service="Spotware", Name="Application", ViewRole=RoleAPI.Editor.name, EditRole=RoleAPI.Editor.name, Secret=CredentialAPI.pack({"ClientSecret": "cs"}))
    child = vault.store(by=EDITOR, Service="Spotware", Name="Account", ViewRole=RoleAPI.Viewer.name, EditRole=RoleAPI.Editor.name, Parent=parent.UID, Secret=CredentialAPI.pack({"AccessToken": "at"}))
    assert vault.resolve(uid=child.UID, by=EDITOR)["ClientSecret"].Value == "cs"
    assert vault.resolve(uid=child.UID, by=VIEWER) is None

def test_a_parent_with_children_cannot_be_deleted(vault, stored):
    parent = vault.store(by=ADMIN, Service="Spotware", Name="Application")
    vault.store(by=ADMIN, Service="Spotware", Name="Account", Parent=parent.UID)
    with pytest.raises(ValueError, match="inherit from it"):
        vault.delete(parent.UID, by=ADMIN)

def test_resolve_names_its_target(vault, stored):
    vault.store(by=ADMIN, Service="Spotware", Name="Demo", Secret=CredentialAPI.pack("x"))
    with pytest.raises(ValueError, match="Service and Name"):
        vault.resolve(by=ADMIN)
    with pytest.raises(ValueError, match="Service and Name"):
        vault.resolve(service="Spotware", by=ADMIN)
    assert vault.resolve(service="Spotware", name="Demo", by=ADMIN)["Password"].Value == "x"
    assert vault.resolve(service="Spotware", name="Missing", by=ADMIN) is None

def test_expiry_accepts_the_display_format_and_iso(vault, stored):
    shown = vault.store(by=ADMIN, Service="Framework", Name="Shown", ExpiresAt="2026-12-31 00:00:00")
    assert shown.ExpiresAt == datetime(2026, 12, 31)
    zoned = vault.store(by=ADMIN, Service="Framework", Name="Zoned", ExpiresAt="2026-12-31T00:00:00+02:00")
    assert zoned.ExpiresAt == datetime(2026, 12, 30, 22)
    with pytest.raises(ValueError, match="is not a date"):
        vault.store(by=ADMIN, Service="Framework", Name="Broken", ExpiresAt="2026-12-31 00-00-00")
    assert vault.update(shown.UID, by=ADMIN, ExpiresAt=None) is not None
    assert vault.credential(shown.UID, by=ADMIN)["ExpiresAt"] is None

def test_an_edit_without_a_secret_keeps_it(vault, stored):
    credential = vault.store(by=ADMIN, Service="Spotware", Name="Kept", Kind=CredentialType.OAuth2.name, Secret=CredentialAPI.pack({"ClientSecret": "cs", "AccessToken": "at"}))
    vault.update(credential.UID, by=ADMIN, Name="Renamed", Secret=None)
    assert vault.reveal(credential.UID, by=ADMIN) == {"ClientSecret": "cs", "AccessToken": "at"}

def test_a_secret_object_changes_only_the_keys_it_names(vault, stored):
    credential = vault.store(by=ADMIN, Service="Spotware", Name="Merged", Kind=CredentialType.OAuth2.name,
                               Secret=CredentialAPI.pack({"ClientSecret": "cs", "AccessToken": "at", "RefreshToken": "rt"}))
    vault.update(credential.UID, by=ADMIN, Secret=CredentialAPI.pack({"AccessToken": "new", "RefreshToken": None}))
    assert vault.reveal(credential.UID, by=ADMIN) == {"ClientSecret": "cs", "AccessToken": "new"}
    vault.update(credential.UID, by=ADMIN, Secret=CredentialAPI.pack("replaced"))
    assert vault.reveal(credential.UID, by=ADMIN) == {"ClientSecret": "replaced"}

def test_only_the_owner_or_an_administrator_transfers(vault, stored):
    credential = vault.store(by=MODERATOR, Service="Framework", Name="Shared", ViewRole=RoleAPI.Editor.name, EditRole=RoleAPI.Editor.name)
    with pytest.raises(PermissionError, match="Only the owner or an Administrator"):
        vault.transfer(credential.UID, EDITOR, by=EDITOR)
    with pytest.raises(ValueError, match="is not a user"):
        vault.transfer(credential.UID, "stranger@test.com", by=MODERATOR)
    assert vault.transfer(credential.UID, EDITOR, by=MODERATOR) is True
    assert vault.credential(credential.UID, by=ADMIN)["Owner"] == EDITOR

def test_rows_carry_the_access_of_whoever_reads_them(vault, stored):
    vault.store(by=EDITOR, Service="Framework", Name="Shared", ViewRole=RoleAPI.Viewer.name, EditRole=RoleAPI.Editor.name)
    assert [row["Access"] for row in vault.credentials(by=VIEWER)] == ["View"]
    assert [row["Access"] for row in vault.credentials(by=EDITOR)] == ["Edit"]
    assert [row["Access"] for row in vault.credentials(by=ADMIN)] == ["Edit"]

def test_an_unchanged_threshold_above_the_editor_survives_an_edit(vault, stored):
    credential = vault.store(by=ADMIN, Service="Framework", Name="Raised", Owner=EDITOR, ViewRole=RoleAPI.Editor.name, EditRole=RoleAPI.Administrator.name)
    assert vault.update(credential.UID, by=EDITOR, Name="Renamed", ViewRole=RoleAPI.Editor.name, EditRole=RoleAPI.Administrator.name) is not None
    with pytest.raises(ValueError, match="above your own role"):
        vault.update(credential.UID, by=EDITOR, ViewRole=RoleAPI.Moderator.name)

def test_validity_reads_the_expiry_against_the_refresh_margin():
    now, vault = datetime(2026, 9, 23, 12), VaultAPI(database=DATABASE)
    assert vault.validity(None, now) is Validity.Permanent
    assert vault.validity(now - timedelta(seconds=1), now) is Validity.Expired
    assert vault.validity(now + timedelta(days=3), now) is Validity.Expiring
    assert vault.validity(now + timedelta(days=30), now) is Validity.Valid
    assert VaultAPI(database=DATABASE, margin=86400).validity(now + timedelta(days=3), now) is Validity.Valid

def test_a_refresher_is_given_to_the_vault_not_registered_globally(vault, stored):
    credential = vault.store(by=ADMIN, Service="Rotating", Name="Token", Kind=CredentialType.OAuth2.name, Secret=CredentialAPI.pack({"AccessToken": "old"}), ExpiresAt=utc_now())
    assert vault.rotate(credential.UID) is False
    rotating = VaultAPI(database=DATABASE, refreshers={"Rotating": lambda values: ({"AccessToken": "new"}, utc_now() + timedelta(days=30))})
    assert rotating.rotate(credential.UID) is True
    assert vault.reveal(credential.UID, by=ADMIN) == {"AccessToken": "new"}