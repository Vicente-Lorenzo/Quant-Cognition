import dash
import pytest

from Library.Auth import AccessAPI, RoleAPI
from Library.Credential import CredentialAPI, CredentialType, SecretAPI

@pytest.fixture(scope="module")
def page(application):
    return application._pages_["/framework/credential/"]

def test_the_page_is_a_viewer_page(page):
    assert page.access is RoleAPI.Viewer
    assert page.endpoint == "/framework/credential/"

def test_the_grid_masks_every_secret(page):
    row = page._row_({"UID": "x", "Service": "Spotware", "Name": "Demo", "Kind": CredentialType.OAuth2.name,
                      "Username": CredentialAPI.pack({"ClientId": "cid"}),
                      "Secret": CredentialAPI.pack({"ClientSecret": SecretAPI.MASK}),
                      "Owner": "vicente", "ViewRole": RoleAPI.Viewer.name, "EditRole": RoleAPI.Editor.name})
    assert row["Username"] == "ClientId: cid"
    assert row["Secret"] == f"ClientSecret: {SecretAPI.MASK}"
    assert row["View"] == "Viewer" and row["Edit"] == "Editor"

def test_a_null_threshold_reads_as_owner_only(page):
    row = page._row_({"UID": "x", "Service": "Framework", "Name": "Private", "Kind": CredentialType.Password.name,
                      "Username": None, "Secret": None, "Owner": "vicente", "ViewRole": None, "EditRole": None})
    assert row["View"] == AccessAPI.label(None) and row["Edit"] == AccessAPI.label(None)
    assert row["Secret"] == SecretAPI.MASK

def test_the_role_choices_offer_owner_only_and_never_public(page):
    values = [choice["value"] for choice in page._roles_()]
    assert values[0] == "" and RoleAPI.Public.name not in values
    assert values[1:] == [RoleAPI.Viewer.name, RoleAPI.Editor.name, RoleAPI.Moderator.name, RoleAPI.Administrator.name]

def test_a_refused_reveal_notifies_instead_of_silently_stopping(page, monkeypatch):
    messages = []
    monkeypatch.setattr(page._vault_, "reveal", lambda uid, by=None: None)
    monkeypatch.setattr(page, "_actor_", lambda: "viewer@test.com")
    monkeypatch.setattr(page.app.notify, "error", lambda message, **kwargs: messages.append(message))
    assert page._reveal_(1, {"selected": ["some-uid"]}) is dash.no_update
    assert messages == ["You may not reveal this credential"]

def test_a_reveal_renders_one_row_per_secret(page, monkeypatch):
    monkeypatch.setattr(page._vault_, "reveal", lambda uid, by=None: {"ClientSecret": "cs", "AccessToken": "at"})
    monkeypatch.setattr(page, "_actor_", lambda: "admin@test.com")
    rendered = page._reveal_(1, {"selected": ["some-uid"]})
    assert [child.children[0].children for child in rendered] == ["ClientSecret", "AccessToken"]
    assert [child.children[1].children for child in rendered] == ["cs", "at"]

def test_hiding_restores_the_mask(page):
    assert page._hide_(1).children == SecretAPI.MASK

def test_the_grid_carries_the_readers_access(page):
    assert "Access" in page._COLUMNS_
    assert page._row_({"UID": "x", "Service": "S", "Name": "N", "Kind": "Password", "Access": "View"})["Access"] == "View"

def test_editing_never_prefills_the_secret(page, monkeypatch):
    row = {"UID": "x", "Service": "Spotware", "Name": "Demo", "Kind": CredentialType.OAuth2.name, "Username": CredentialAPI.pack({"ClientId": "cid"}),
           "Secret": CredentialAPI.pack({"ClientSecret": SecretAPI.MASK}), "Fields": None, "ExpiresAt": None, "Parent": None, "Owner": "owner@test.com",
           "ViewRole": RoleAPI.Viewer.name, "EditRole": None, "Access": "Edit"}
    monkeypatch.setattr(page._vault_, "credential", lambda uid, by=None: row)
    monkeypatch.setattr(page, "_actor_", lambda: "owner@test.com")
    opened = dict(zip(["open", "mode", "title", *[entry.name for entry in page._FIELDS_]], page._open_(1, {"selected": ["x"]})))
    assert opened["secret"] == "" and opened["username"] == CredentialAPI.pack({"ClientId": "cid"})
    assert opened["owner"] == "owner@test.com" and opened["view"] == "Viewer" and opened["edit"] == ""

def test_a_view_only_row_cannot_be_opened_for_edit(page, monkeypatch):
    messages = []
    monkeypatch.setattr(page._vault_, "credential", lambda uid, by=None: {"UID": "x", "Access": "View"})
    monkeypatch.setattr(page, "_actor_", lambda: "viewer@test.com")
    monkeypatch.setattr(page.app.notify, "error", lambda message, **kwargs: messages.append(message))
    assert page._open_(1, {"selected": ["x"]})[0] is dash.no_update
    assert messages == ["You may not edit this credential"]

def test_saving_parses_values_and_leaves_an_empty_secret_alone(page, monkeypatch):
    calls = []
    monkeypatch.setattr(page._vault_, "update", lambda uid, by=None, **fields: calls.append(fields) or fields)
    monkeypatch.setattr(page, "_actor_", lambda: "owner@test.com")
    monkeypatch.setattr(page.app.notify, "success", lambda message, **kwargs: None)
    values = (" Spotware ", "Demo", "OAuth2", '{"ClientId": "cid"}', "", '{"Host": "demo.ctraderapi.com"}', "2026-12-31 00:00:00", "", "owner@test.com", "Viewer", "Editor")
    assert page._save_(1, {"mode": "update", "uid": "x"}, *values)[0] is False
    saved = calls[0]
    assert saved["Service"] == "Spotware" and saved["Secret"] is None
    assert CredentialAPI.unpack(saved["Username"]) == {"ClientId": "cid"} and CredentialAPI.unpack(saved["Fields"]) == {"Host": "demo.ctraderapi.com"}
    assert saved["ExpiresAt"] == "2026-12-31 00:00:00" and saved["ViewRole"] == "Viewer" and saved["EditRole"] == "Editor"

def test_a_numeric_looking_secret_stays_text(page):
    assert CredentialAPI.unpack(page._entry_("12345", "Secret")) == "12345"
    assert CredentialAPI.unpack(page._entry_("hunter2", "Secret")) == "hunter2"

def test_fields_must_be_a_json_object(page, monkeypatch):
    messages = []
    monkeypatch.setattr(page, "_actor_", lambda: "owner@test.com")
    monkeypatch.setattr(page.app.notify, "error", lambda message, **kwargs: messages.append(message))
    values = ("Spotware", "Demo", "Password", "", "", "not json", "", "", "", "", "")
    assert page._save_(1, {"mode": "create"}, *values) == (dash.no_update, dash.no_update)
    assert messages == ["Credential Fields: Failed · Expected a JSON object"]

def test_a_refused_store_is_reported(page, monkeypatch):
    messages = []
    def refuse(by=None, **fields): raise PermissionError("Access Owner: Failed · Only an Administrator may assign x as owner")
    monkeypatch.setattr(page._vault_, "store", refuse)
    monkeypatch.setattr(page, "_actor_", lambda: "editor@test.com")
    monkeypatch.setattr(page.app.notify, "error", lambda message, **kwargs: messages.append(message))
    values = ("Spotware", "Demo", "Password", "", "x", "", "", "", "x", "", "")
    assert page._save_(1, {"mode": "create"}, *values) == (dash.no_update, dash.no_update)
    assert messages and messages[0].startswith("Access Owner: Failed")

def test_expiry_renders_in_the_display_format(page):
    from datetime import datetime
    assert page._stamp_(datetime(2026, 12, 31, 8, 30)) == "2026-12-31 08:30:00"

def test_a_new_selection_conceals_a_revealed_secret(page):
    assert page._conceal_({"selected": ["y"]}).children == SecretAPI.MASK

def test_validity_is_an_icon_and_a_label(page):
    badge = page._validity_(None)
    assert "led-none" in badge and "Permanent" in badge
    assert "Validity" in page._markdown_columns_()

def test_the_kind_drives_the_key_templates(page):
    username, secret = page._template_(CredentialType.OAuth2.name)
    assert CredentialAPI.unpack(username) == {"ClientId": "", "AccountId": ""}
    assert CredentialAPI.unpack(secret) == {"ClientSecret": "", "AccessToken": "", "RefreshToken": ""}