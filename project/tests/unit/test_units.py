import pytest

from cfd_workflow.parser.units import (
    length_to_meters,
    parse_length,
    parse_velocity,
    velocity_to_ms,
)


@pytest.mark.parametrize(
    "value,unit,expected",
    [
        (1.0, "m", 1.0),
        (100.0, "cm", 1.0),
        (5.0, "cm", 0.05),
        (10.0, "mm", 0.01),
        (0.1, "米", 0.1),
        (5.0, "厘米", 0.05),
        (1000.0, "mm", 1.0),
        (2.5, "m", 2.5),
    ],
)
def test_length_to_meters(value, unit, expected):
    assert length_to_meters(value, unit) == pytest.approx(expected)


@pytest.mark.parametrize(
    "value,unit,expected",
    [
        (1.0, "m/s", 1.0),
        (2.0, "mps", 2.0),
        (1.5, "米/秒", 1.5),
        (3.0, "米每秒", 3.0),
    ],
)
def test_velocity_to_ms(value, unit, expected):
    assert velocity_to_ms(value, unit) == pytest.approx(expected)


def test_parse_length_from_text():
    q = parse_length("圆柱直径0.1米")
    assert q is not None
    assert q.value == pytest.approx(0.1)
    assert q.unit == "米"


def test_parse_velocity_from_text():
    q = parse_velocity("来流速度1米每秒")
    assert q is not None
    assert q.value == pytest.approx(1.0)


def test_unsupported_length_unit():
    with pytest.raises(ValueError):
        length_to_meters(1.0, "inch")
