from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class FluidType(str, Enum):
    AIR = "air"
    WATER = "water"


class SimulationDimension(str, Enum):
    TWO_D = "2d"
    THREE_D = "3d"


DEFAULT_SPAN_RATIO = 10.0


class ParsedParams(BaseModel):
    """Raw parameters extracted from natural language input."""

    diameter_m: Optional[float] = Field(default=None, description="Cylinder diameter in meters")
    radius_m: Optional[float] = Field(default=None, description="Cylinder radius in meters")
    reynolds: Optional[float] = Field(default=None, description="Reynolds number")
    velocity_ms: Optional[float] = Field(default=None, description="Inlet velocity in m/s")
    fluid: Optional[FluidType] = Field(default=None, description="Fluid type")
    dimension: Optional[SimulationDimension] = Field(
        default=None,
        description="2D or 3D simulation; None defaults to 2D unless span is given",
    )
    span_m: Optional[float] = Field(
        default=None,
        description="Cylinder span along z-axis in meters (3D)",
    )


class CompleteParams(BaseModel):
    """Fully specified parameters ready for simulation."""

    diameter_m: float
    reynolds: float
    velocity_ms: float
    fluid: FluidType
    kinematic_viscosity_m2s: float
    density_kgm3: float
    dimension: SimulationDimension = SimulationDimension.TWO_D
    span_m: Optional[float] = Field(
        default=None,
        description="Cylinder span along z (3D only); L/D aspect ratio end effects",
    )

    @property
    def radius_m(self) -> float:
        return self.diameter_m / 2.0

    @property
    def span_ratio(self) -> Optional[float]:
        if self.span_m is None or self.diameter_m <= 0:
            return None
        return self.span_m / self.diameter_m
