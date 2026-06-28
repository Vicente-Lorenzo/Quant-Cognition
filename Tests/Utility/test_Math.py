import pytest

from Library.Utility.Math import equals, truncate

def test_equals():
    assert equals(1.0, 1.0) is True
    assert equals(1.0, 1.0 + 1e-13) is True
    assert equals(1.0, 1.0 + 1e-6) is False

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
