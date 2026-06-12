import pytest

from cfd_workflow.models import FluidType, ParsedParams
from cfd_workflow.physics.parameters import (
    complete_parameters,
    fluid_properties,
    missing_fields_prompt,
    validate_parameters,
)


def test_fluid_properties_air():
    nu, rho = fluid_properties(FluidType.AIR)
    assert nu == pytest.approx(1.5e-5)
    assert rho == pytest.approx(1.225)


def test_fluid_properties_water():
    nu, rho = fluid_properties(FluidType.WATER)
    assert nu == pytest.approx(1.0e-6)
    assert rho == pytest.approx(998.0)


def test_complete_from_re_u_diameter():
    parsed = ParsedParams(diameter_m=0.1, reynolds=100.0, velocity_ms=1.0)
    complete = complete_parameters(parsed)
    assert complete.diameter_m == pytest.approx(0.1)
    assert complete.reynolds == pytest.approx(100.0)
    assert complete.velocity_ms == pytest.approx(1.0)
    assert complete.fluid == FluidType.AIR


def test_complete_re_from_velocity_and_diameter():
    parsed = ParsedParams(diameter_m=0.1, velocity_ms=1.0)
    complete = complete_parameters(parsed)
    expected_re = 1.0 * 0.1 / 1.5e-5
    assert complete.reynolds == pytest.approx(expected_re)


def test_complete_velocity_from_re_and_diameter():
    parsed = ParsedParams(diameter_m=0.1, reynolds=100.0)
    complete = complete_parameters(parsed)
    expected_u = 100.0 * 1.5e-5 / 0.1
    assert complete.velocity_ms == pytest.approx(expected_u)


def test_complete_from_radius():
    parsed = ParsedParams(radius_m=0.05, reynolds=150.0, velocity_ms=1.5, fluid=FluidType.WATER)
    complete = complete_parameters(parsed)
    assert complete.diameter_m == pytest.approx(0.1)
    assert complete.fluid == FluidType.WATER


def test_complete_water_example():
    parsed = ParsedParams(diameter_m=0.1, reynolds=150.0, velocity_ms=1.5, fluid=FluidType.WATER)
    complete = complete_parameters(parsed)
    assert complete.kinematic_viscosity_m2s == pytest.approx(1.0e-6)


def test_missing_diameter_raises():
    parsed = ParsedParams(reynolds=100.0, velocity_ms=1.0)
    with pytest.raises(ValueError, match="diameter"):
        complete_parameters(parsed)


def test_missing_re_and_velocity_raises():
    parsed = ParsedParams(diameter_m=0.1)
    with pytest.raises(ValueError):
        complete_parameters(parsed)


def test_validate_parameters_ok():
    parsed = ParsedParams(diameter_m=0.1, reynolds=100.0, velocity_ms=1.0)
    complete = complete_parameters(parsed)
    assert validate_parameters(complete) == []


def test_missing_fields_prompt():
    assert missing_fields_prompt(ParsedParams()) is not None
    assert "直径" in missing_fields_prompt(ParsedParams())
    assert missing_fields_prompt(ParsedParams(diameter_m=0.1, velocity_ms=1.0)) is None
