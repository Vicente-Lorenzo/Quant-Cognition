import pytest

from Library.Utility.Range import RangeAPI

def test_sequence_is_inclusive_and_keeps_integers():
    assert RangeAPI.sequence(5, 20, 5) == [5, 10, 15, 20]

def test_sequence_keeps_floats_when_any_bound_is_fractional():
    assert RangeAPI.sequence(0.5, 2.0, 0.5) == [0.5, 1.0, 1.5, 2.0]

def test_sequence_never_returns_empty():
    assert RangeAPI.sequence(10, 5, 1) == [10]

def test_window_centers_on_a_value():
    assert RangeAPI.window(20, -4, 4, 2) == [16, 18, 20, 22, 24]

def test_window_clamps_to_the_declared_bounds():
    assert RangeAPI.window(6, -20, 20, 2, floor=5, ceiling=50) == [6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26]

@pytest.mark.parametrize("text, expected", [("5-50:5", (5, 50, 5)), ("5..50:5", (5, 50, 5)),
                                            ("0.5..2.0:0.5", (0.5, 2.0, 0.5)), ("5-20", (5, 20, 1))])
def test_parse_accepts_both_separators(text, expected):
    parsed = RangeAPI.parse(text)
    assert (parsed.Low, parsed.High, parsed.Step) == expected

@pytest.mark.parametrize("text", ["SMA", "50-5", "", "Auto", "5:5"])
def test_parse_rejects_anything_that_is_not_a_range(text):
    assert RangeAPI.parse(text) is None

def test_parse_is_idempotent():
    parsed = RangeAPI.parse("5-50:5")
    assert RangeAPI.parse(parsed) is parsed

def test_parse_ignores_non_strings():
    assert RangeAPI.parse(["SMA", 20]) is None
    assert RangeAPI.parse(20) is None

def test_ladder_halves_an_integer_step_down_to_one():
    assert RangeAPI.parse("5-50:5").ladder() == ((5, 50, 5), (-4, 4, 2), (-2, 2, 1))

def test_ladder_stops_when_the_step_is_already_one():
    assert RangeAPI.parse("5-20").ladder() == ((5, 20, 1),)

def test_ladder_halves_a_fractional_step_exactly():
    assert RangeAPI.parse("0.5..2.0:0.5").ladder() == ((0.5, 2.0, 0.5), (-0.5, 0.5, 0.25), (-0.25, 0.25, 0.125))

def test_a_parsed_range_walks_its_first_round():
    parsed = RangeAPI.parse("10-30:10")
    assert RangeAPI.sequence(*parsed.ladder()[0]) == [10, 20, 30]