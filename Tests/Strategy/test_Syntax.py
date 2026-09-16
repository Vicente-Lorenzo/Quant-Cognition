from Library.Strategy.Syntax import SyntaxAPI

def test_slots_render_with_the_house_separator():
    assert SyntaxAPI.format_slots([["SMA", "EMA"], [10, 20]]) == "SMA|EMA · 10|20"

def test_slots_round_trip_to_an_equivalent_space():
    assert SyntaxAPI.parse_slots(SyntaxAPI.format_slots([["SMA", "EMA"], [10, 20]])) == [["SMA", "EMA"], [10, 20]]
    assert SyntaxAPI.parse_slots(SyntaxAPI.format_slots(["ATR", 14])) == ["ATR", 14]

def test_a_semicolon_is_accepted_because_the_separator_is_not_on_a_keyboard():
    assert SyntaxAPI.parse_slots("SMA|EMA ; 10|20") == SyntaxAPI.parse_slots("SMA|EMA · 10|20")

def test_a_single_option_slot_collapses_to_a_scalar():
    assert SyntaxAPI.parse_slots("SMA · Auto") == ["SMA", "Auto"]

def test_an_empty_slot_text_is_no_slots():
    assert SyntaxAPI.parse_slots("   ") == []

def test_numbers_decode_and_text_survives():
    assert SyntaxAPI.parse_slots("ATR · 14 · 0.5 · Signal") == ["ATR", 14, 0.5, "Signal"]

def test_numbered_recognizes_a_staged_body():
    assert SyntaxAPI.numbered({"1": {}, "2-3": {}}) is True
    assert SyntaxAPI.numbered({"Baseline": []}) is False
    assert SyntaxAPI.numbered({}) is False
    assert SyntaxAPI.numbered(None) is False