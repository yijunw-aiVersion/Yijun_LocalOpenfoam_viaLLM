"""Length and velocity unit parsing and conversion."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Quantity:
    value: float
    unit: str


_LENGTH_TO_METERS = {
    "m": 1.0,
    "meter": 1.0,
    "meters": 1.0,
    "metre": 1.0,
    "metres": 1.0,
    "米": 1.0,
    "cm": 0.01,
    "centimeter": 0.01,
    "centimeters": 0.01,
    "厘米": 0.01,
    "mm": 0.001,
    "millimeter": 0.001,
    "millimeters": 0.001,
    "毫米": 0.001,
}

_VELOCITY_TO_MS = {
    "m/s": 1.0,
    "mps": 1.0,
    "ms": 1.0,
    "米/秒": 1.0,
    "米每秒": 1.0,
    "米/ s": 1.0,
}


def normalize_length_unit(unit: str) -> str:
    return unit.strip().lower()


def length_to_meters(value: float, unit: str) -> float:
    key = normalize_length_unit(unit)
    if key not in _LENGTH_TO_METERS:
        raise ValueError(f"Unsupported length unit: {unit}")
    return value * _LENGTH_TO_METERS[key]


def normalize_velocity_unit(unit: str) -> str:
    return unit.strip().lower().replace(" ", "")


def velocity_to_ms(value: float, unit: str) -> float:
    key = normalize_velocity_unit(unit)
    if key not in _VELOCITY_TO_MS:
        raise ValueError(f"Unsupported velocity unit: {unit}")
    return value * _VELOCITY_TO_MS[key]


def parse_length(text: str) -> Optional[Quantity]:
    """Extract a length quantity from text, returned in original units."""
    patterns = [
        r"(\d+(?:\.\d+)?)\s*(米|m|cm|厘米|mm|毫米|meter|meters|centimeter|centimeters|millimeter|millimeters)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            value = float(match.group(1))
            unit = match.group(2)
            return Quantity(value=value, unit=unit)
    return None


def parse_velocity(text: str) -> Optional[Quantity]:
    """Extract velocity from text."""
    patterns = [
        r"(\d+(?:\.\d+)?)\s*(m/s|mps|米/秒|米每秒|米/s|ms-1|m\s*s-1)",
        r"速度\s*(\d+(?:\.\d+)?)\s*(米/秒|米每秒|m/s|mps)",
        r"流速\s*(\d+(?:\.\d+)?)\s*(米/秒|米每秒|m/s|mps|米/s)?",
        r"来流速度\s*(\d+(?:\.\d+)?)\s*(米/秒|米每秒|m/s|mps|米/s|米)?",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            value = float(match.group(1))
            unit = match.group(2) if match.lastindex >= 2 and match.group(2) else "m/s"
            if unit in {"米"}:
                unit = "米/秒"
            return Quantity(value=value, unit=unit)
    return None
