from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class FluidType(str, Enum):
    AIR = "air"
    WATER = "water"


class ParsedParams(BaseModel):
    """Raw parameters extracted from natural language input."""

    diameter_m: Optional[float] = Field(default=None, description="Cylinder diameter in meters")
    radius_m: Optional[float] = Field(default=None, description="Cylinder radius in meters")
    reynolds: Optional[float] = Field(default=None, description="Reynolds number")
    velocity_ms: Optional[float] = Field(default=None, description="Inlet velocity in m/s")
    fluid: Optional[FluidType] = Field(default=None, description="Fluid type")


class CompleteParams(BaseModel):
    """Fully specified parameters ready for simulation."""

    diameter_m: float
    reynolds: float
    velocity_ms: float
    fluid: FluidType
    kinematic_viscosity_m2s: float
    density_kgm3: float

    @property
    def radius_m(self) -> float:
        return self.diameter_m / 2.0
