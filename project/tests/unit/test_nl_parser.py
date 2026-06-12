import pytest

from cfd_workflow.models import FluidType
from cfd_workflow.parser.nl_parser import parse_fluid, parse_nl_input, parse_reynolds
from cfd_workflow.parser.units import parse_velocity


EXAMPLES = [
    (
        "圆柱直径0.1米，雷诺数100，来流速度1米每秒。",
        {"diameter_m": 0.1, "reynolds": 100.0, "velocity_ms": 1.0, "fluid": None},
    ),
    (
        "我想模拟一个直径5厘米的圆柱，流速2m/s，雷诺数200。",
        {"diameter_m": 0.05, "reynolds": 200.0, "velocity_ms": 2.0, "fluid": None},
    ),
    (
        "圆柱半径0.05m，Re=150，U=1.5m/s，流体是水。",
        {"diameter_m": 0.1, "reynolds": 150.0, "velocity_ms": 1.5, "fluid": FluidType.WATER},
    ),
    (
        "模拟空气绕过直径10cm的圆柱，速度3m/s。",
        {"diameter_m": 0.1, "reynolds": None, "velocity_ms": 3.0, "fluid": FluidType.AIR},
    ),
]


@pytest.mark.parametrize("text,expected", EXAMPLES)
def test_problem_description_examples(text, expected):
    parsed = parse_nl_input(text)
    assert parsed.diameter_m == pytest.approx(expected["diameter_m"])
    if expected["reynolds"] is not None:
        assert parsed.reynolds == pytest.approx(expected["reynolds"])
    else:
        assert parsed.reynolds is None
    assert parsed.velocity_ms == pytest.approx(expected["velocity_ms"])
    assert parsed.fluid == expected["fluid"]


@pytest.mark.parametrize(
    "text,expected",
    [
        ("雷诺数100", 100.0),
        ("Re=150", 150.0),
        ("reynolds number: 200", 200.0),
    ],
)
def test_parse_reynolds(text, expected):
    assert parse_reynolds(text) == pytest.approx(expected)


@pytest.mark.parametrize(
    "text,expected",
    [
        ("流体是水", FluidType.WATER),
        ("模拟空气绕过圆柱", FluidType.AIR),
        ("water flow", FluidType.WATER),
    ],
)
def test_parse_fluid(text, expected):
    assert parse_fluid(text) == expected


def test_radius_input_sets_diameter():
    parsed = parse_nl_input("圆柱半径0.05m，Re=150")
    assert parsed.radius_m == pytest.approx(0.05)
    assert parsed.diameter_m == pytest.approx(0.1)


def test_velocity_aliases():
    assert parse_velocity("流速2m/s").value == pytest.approx(2.0)
    assert parse_velocity("速度3米/秒").value == pytest.approx(3.0)
