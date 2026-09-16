import pytest

from Library.Utility.Math import EPSILON, equals, truncate

def test_equals():
    assert equals(1.0, 1.0) is True
    assert equals(1.0, 1.0 + 1e-13) is True
    assert equals(1.0, 1.0 + 1e-6) is False

def test_equals_scales_the_tolerance_with_magnitude_and_floors_it_at_one():
    assert equals(1e6, 1e6 + 1e-3) is True
    assert equals(1e6, 1e6 + 1e-1) is False
    assert equals(0.0, EPSILON) is True
    assert equals(0.0, 2.0 * EPSILON) is False

def test_equals_takes_the_tolerance_as_an_argument():
    assert equals(1.0, 1.001, tolerance=1e-2) is True
    assert equals(1.0, 1.0 + 1e-9, tolerance=0.0) is False

def test_truncate_toward_zero():
    assert truncate(0.315) == pytest.approx(0.31)
    assert truncate(-0.315) == pytest.approx(-0.31)
    assert truncate(0.36) == pytest.approx(0.36)
    assert truncate(0.27) == pytest.approx(0.27)
    assert truncate(-0.629) == pytest.approx(-0.62)
    assert truncate(0.0) == pytest.approx(0.0)

def test_truncate_digits():
    assert truncate(1.23456, 3) == pytest.approx(1.234)
    assert truncate(-1.23456, 3) == pytest.approx(-1.234)
    assert truncate(123.456, 0) == pytest.approx(123.0)
    assert truncate(-123.456, 0) == pytest.approx(-123.0)

def test_truncate_tolerance_recovers_a_unit_lost_to_float_error_from_below():
    assert truncate(0.29999999999) == 0.3
    assert truncate(-0.29999999999) == -0.3
    assert truncate(0.29999999999, tolerance=0.0) == 0.29
    assert truncate(0.2999, tolerance=0.0) == truncate(0.2999)