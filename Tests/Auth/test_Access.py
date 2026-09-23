import pytest

from Library.Auth import AccessLevel, AccessAPI, RoleAPI

NAMES = ("RunRole", "EditRole")

def test_access_levels_run_from_denied_to_edit():
    assert AccessLevel.names() == ["Denied", "View", "Run", "Edit"]

def test_the_roles_never_offer_public():
    assert AccessAPI.roles() == [RoleAPI.Viewer.name, RoleAPI.Editor.name, RoleAPI.Moderator.name, RoleAPI.Administrator.name]

def test_an_empty_threshold_parses_as_owner_only():
    assert AccessAPI.parse(None) is None and AccessAPI.parse("") is None
    assert AccessAPI.parse("Editor") is RoleAPI.Editor
    with pytest.raises(ValueError, match="Unknown role"):
        AccessAPI.parse("Janitor")

def test_a_label_names_the_role_or_owner_only():
    assert AccessAPI.label(None) == "Owner only"
    assert AccessAPI.label(RoleAPI.Moderator.name) == "Moderator"

def test_public_is_refused_on_either_side():
    with pytest.raises(ValueError, match="RunRole cannot be Public"):
        AccessAPI.validate("Public", "Editor", names=NAMES)
    with pytest.raises(ValueError, match="EditRole cannot be Public"):
        AccessAPI.validate("Viewer", "Public", names=NAMES)

def test_the_upper_threshold_is_never_below_the_lower():
    with pytest.raises(ValueError, match="EditRole Viewer is below RunRole Editor"):
        AccessAPI.validate("Editor", "Viewer", names=NAMES)
    assert AccessAPI.validate("Viewer", "Editor", names=NAMES) == (RoleAPI.Viewer, RoleAPI.Editor)
    assert AccessAPI.validate("Viewer", None, names=NAMES) == (RoleAPI.Viewer, None)

def test_an_owner_only_lower_forces_an_owner_only_upper():
    with pytest.raises(ValueError, match="must be owner only"):
        AccessAPI.validate(None, "Editor", names=NAMES)
    assert AccessAPI.validate(None, None, names=NAMES) == (None, None)

def test_a_setter_cannot_grant_above_their_own_role():
    with pytest.raises(ValueError, match="above your own role Editor"):
        AccessAPI.validate("Editor", "Moderator", names=NAMES, setter=RoleAPI.Editor)
    assert AccessAPI.validate("Editor", "Editor", names=NAMES, setter=RoleAPI.Editor) == (RoleAPI.Editor, RoleAPI.Editor)
    assert AccessAPI.validate("Moderator", "Administrator", names=NAMES) == (RoleAPI.Moderator, RoleAPI.Administrator)

def test_a_kept_threshold_is_not_capped_again():
    kept = ("Editor", "Administrator")
    assert AccessAPI.validate("Editor", "Administrator", names=NAMES, setter=RoleAPI.Editor, previous=kept) == (RoleAPI.Editor, RoleAPI.Administrator)
    with pytest.raises(ValueError, match="RunRole Moderator is above"):
        AccessAPI.validate("Moderator", "Administrator", names=NAMES, setter=RoleAPI.Editor, previous=kept)

def test_allows_follows_owner_administrator_then_threshold():
    assert AccessAPI.allows(None, role=RoleAPI.Administrator, user="admin", owner="someone")
    assert AccessAPI.allows(None, role=RoleAPI.Viewer, user="me", owner="me")
    assert not AccessAPI.allows(None, role=RoleAPI.Moderator, user="me", owner="someone")
    assert AccessAPI.allows("Editor", role=RoleAPI.Moderator, user="me", owner="someone")
    assert not AccessAPI.allows("Editor", role=RoleAPI.Viewer, user="me", owner="someone")
    assert not AccessAPI.allows("Public", role=RoleAPI.Viewer, user="me", owner="someone")
    assert not AccessAPI.allows(None, role=RoleAPI.Public, user=None, owner=None)

def test_only_an_administrator_assigns_another_owner():
    AccessAPI.claim("me", role=RoleAPI.Editor, user="me")
    AccessAPI.claim("someone", role=RoleAPI.Administrator, user="admin")
    with pytest.raises(PermissionError, match="may only own what they create"):
        AccessAPI.claim("someone", role=RoleAPI.Editor, user="me")