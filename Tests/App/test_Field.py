from Library.App.V2.Component.Field import ControlType, FieldAPI

_SPEC_ = (
    FieldAPI(name="uid", label="UID", identity=True),
    FieldAPI(name="name", required=True),
    FieldAPI(name="kind", control="select", default="Scheduled", options=[{"label": "Scheduled", "value": "Scheduled"}]),
    FieldAPI(name="maxretry", label="Max Retry", column="MaxRetry", control="number", default=0),
    FieldAPI(name="waits", control="switch", default=True),
    FieldAPI(name="relative", control="switch", stored=False, rendered=False, default=False),
)

def test_control_accepts_a_lowercase_value():
    assert FieldAPI(name="x", control="select").control is ControlType.Select

def test_control_defaults_to_text():
    assert FieldAPI(name="x").control is ControlType.Text

def test_attribute_and_identifier_derive_from_the_name():
    entry = FieldAPI(name="maxretry")
    assert entry.attribute == "F_MAXRETRY"
    assert entry.id.name == "F_MAXRETRY"

def test_label_defaults_to_a_titled_name():
    assert FieldAPI(name="retry_delay").label == "Retry Delay"

def test_column_defaults_to_the_label_without_spaces():
    assert FieldAPI(name="requires_approval").column == "RequiresApproval"

def test_explicit_column_wins():
    assert FieldAPI(name="workflow", column="WID").column == "WID"

def test_switch_is_reported():
    assert FieldAPI(name="waits", control="switch").switched is True
    assert FieldAPI(name="name").switched is False

def test_index_maps_names_to_entries():
    assert FieldAPI.index(_SPEC_)["kind"].column == "Kind"

def test_default_may_be_a_callable_resolved_against_the_page():
    entry = FieldAPI(name="owner", default=lambda page: page.owner)
    assert entry.initial(type("Page", (), {"owner": "me"})) == "me"

def test_read_falls_back_to_the_default():
    assert _SPEC_[3].read({}) == 0
    assert _SPEC_[3].read({"MaxRetry": 5}) == 5

def test_read_of_a_switch_defaulting_true_treats_absence_as_true():
    assert _SPEC_[4].read({}) is True
    assert _SPEC_[4].read({"Waits": False}) is False

def test_read_of_a_switch_defaulting_false_treats_absence_as_false():
    assert _SPEC_[5].read({}) is False

def test_read_honors_a_decoder():
    entry = FieldAPI(name="workflow", column="WID", decode=lambda row: row.get("WID") or "")
    assert entry.read({"WID": None}) == ""

def test_write_blanks_empty_text_to_none():
    assert _SPEC_[1].write("") is None
    assert _SPEC_[1].write("Alpha") == "Alpha"

def test_write_zeroes_an_empty_number():
    assert _SPEC_[3].write(None) == 0

def test_write_coerces_a_switch_to_bool():
    assert _SPEC_[4].write(1) is True

def test_write_honors_an_encoder():
    assert FieldAPI(name="x", encode=lambda value: value.upper()).write("a") == "A"

def test_payload_skips_the_identity_and_unstored_entries():
    payload = FieldAPI.payload(_SPEC_, ("uid-1", "Alpha", "Manual", 2, True, True))
    assert payload == {"Name": "Alpha", "Kind": "Manual", "MaxRetry": 2, "Waits": True}

def test_missing_reports_nothing_when_satisfied():
    assert FieldAPI.missing(_SPEC_, ("uid-1", "Alpha", "Manual", 0, True, False)) is None

def test_missing_names_one_absent_field():
    assert FieldAPI.missing(_SPEC_, ("uid-1", "", "Manual", 0, True, False)) == "Name"

def test_missing_joins_several_absent_fields():
    spec = (FieldAPI(name="a", required=True), FieldAPI(name="b", required=True), FieldAPI(name="c", required=True))
    assert FieldAPI.missing(spec, ("", "", "")) == "A, B and C"