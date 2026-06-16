"""Physical parameter completion and validation."""

from __future__ import annotations

from typing import Optional

from cfd_workflow.models import (
    DEFAULT_SPAN_RATIO,
    CompleteParams,
    FluidType,
    ParsedParams,
    SimulationDimension,
)

# Standard properties at ~20°C
FLUID_PROPERTIES = {
    FluidType.AIR: {"nu": 1.5e-5, "rho": 1.225},
    FluidType.WATER: {"nu": 1.0e-6, "rho": 998.0},
}

DEFAULT_FLUID = FluidType.AIR


def fluid_properties(fluid: FluidType) -> tuple[float, float]:
    props = FLUID_PROPERTIES[fluid]
    return props["nu"], props["rho"]


def resolve_dimension(
    parsed: ParsedParams,
    dimension_override: Optional[SimulationDimension] = None,
) -> SimulationDimension:
    if dimension_override is not None:
        return dimension_override
    if parsed.dimension is not None:
        return parsed.dimension
    return SimulationDimension.TWO_D


def resolve_span_m(
    parsed: ParsedParams,
    diameter_m: float,
    dimension: SimulationDimension,
    span_override: Optional[float] = None,
) -> Optional[float]:
    if dimension == SimulationDimension.TWO_D:
        return None
    if span_override is not None:
        return span_override
    if parsed.span_m is not None:
        return parsed.span_m
    return DEFAULT_SPAN_RATIO * diameter_m


def complete_parameters(
    parsed: ParsedParams,
    fluid_override: Optional[FluidType] = None,
    dimension_override: Optional[SimulationDimension] = None,
    span_override: Optional[float] = None,
) -> CompleteParams:
    fluid = fluid_override or parsed.fluid or DEFAULT_FLUID
    nu, rho = fluid_properties(fluid)

    diameter_m = parsed.diameter_m
    if diameter_m is None and parsed.radius_m is not None:
        diameter_m = 2.0 * parsed.radius_m

    reynolds = parsed.reynolds
    velocity_ms = parsed.velocity_ms

    if diameter_m is None:
        raise ValueError("Missing cylinder diameter or radius")

    if reynolds is None and velocity_ms is not None:
        reynolds = velocity_ms * diameter_m / nu
    elif velocity_ms is None and reynolds is not None:
        velocity_ms = reynolds * nu / diameter_m
    elif reynolds is None and velocity_ms is None:
        raise ValueError("Need at least two of: Reynolds number, velocity, or derivable pair with diameter")

    if reynolds is None or velocity_ms is None:
        raise ValueError("Unable to complete parameters")

    dimension = resolve_dimension(parsed, dimension_override=dimension_override)
    span_m = resolve_span_m(
        parsed,
        diameter_m,
        dimension,
        span_override=span_override,
    )

    return CompleteParams(
        diameter_m=diameter_m,
        reynolds=reynolds,
        velocity_ms=velocity_ms,
        fluid=fluid,
        kinematic_viscosity_m2s=nu,
        density_kgm3=rho,
        dimension=dimension,
        span_m=span_m,
    )


def validate_parameters(params: CompleteParams) -> list[str]:
    errors: list[str] = []
    if params.diameter_m <= 0:
        errors.append("Diameter must be positive")
    if params.reynolds <= 0:
        errors.append("Reynolds number must be positive")
    if params.velocity_ms <= 0:
        errors.append("Velocity must be positive")
    if params.reynolds > 1e6:
        errors.append("Reynolds number too high for laminar prototype defaults")
    if params.dimension == SimulationDimension.THREE_D:
        if params.span_m is None or params.span_m <= 0:
            errors.append("3D simulation requires a positive cylinder span")
        elif params.span_ratio is not None and params.span_ratio < 2.0:
            errors.append("3D span L/D should be at least 2 for meaningful finite-cylinder flow")
    return errors


def parameter_warnings(params: CompleteParams) -> list[str]:
    """Non-fatal guidance for setup review."""
    warnings: list[str] = []
    if params.dimension == SimulationDimension.THREE_D:
        ratio = params.span_ratio or 0.0
        warnings.append(
            f"3D finite-cylinder run (L={params.span_m:.4g} m, L/D={ratio:.1f}) — "
            "expect longer runtime than 2D"
        )
        if ratio < 5.0:
            warnings.append(
                f"L/D={ratio:.1f} is short; end effects will be strong vs an infinite 2D cylinder"
            )
    return warnings


def missing_fields_prompt(parsed: ParsedParams) -> Optional[str]:
    missing: list[str] = []
    if parsed.diameter_m is None and parsed.radius_m is None:
        missing.append("圆柱直径或半径")
    if parsed.reynolds is None and parsed.velocity_ms is None:
        missing.append("雷诺数或来流速度")
    if not missing:
        return None
    return "请补充以下参数：" + "、".join(missing)
