"""Natural language parser for CFD simulation parameters."""

from __future__ import annotations

import re
from typing import Optional

from cfd_workflow.models import FluidType, ParsedParams, SimulationDimension
from cfd_workflow.parser.units import length_to_meters, parse_length, parse_velocity, velocity_to_ms


def parse_reynolds(text: str) -> Optional[float]:
    patterns = [
        r"雷诺数\s*[:=]?\s*(\d+(?:\.\d+)?)",
        r"\bRe\s*[:=]?\s*(\d+(?:\.\d+)?)",
        r"reynolds\s*(?:number)?\s*[:=]?\s*(\d+(?:\.\d+)?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return float(match.group(1))
    return None


def parse_fluid(text: str) -> Optional[FluidType]:
    lowered = text.lower()
    if re.search(r"水|water", lowered):
        return FluidType.WATER
    if re.search(r"空气|air", lowered):
        return FluidType.AIR
    return None


def parse_dimension(text: str) -> Optional[SimulationDimension]:
    lowered = text.lower()
    if re.search(r"三维|三d|3d|3\s*维|three.?dimension", lowered):
        return SimulationDimension.THREE_D
    if re.search(r"二维|二d|2d|2\s*维|two.?dimension", lowered):
        return SimulationDimension.TWO_D
    return None


def parse_span(text: str) -> Optional[float]:
    """Parse cylinder span / length along the z-axis (meters)."""
    patterns = [
        r"柱长\s*(\d+(?:\.\d+)?)\s*(米|m|cm|厘米|mm|毫米|meter|meters|centimeter|centimeters|millimeter|millimeters)?",
        r"跨度\s*(\d+(?:\.\d+)?)\s*(米|m|cm|厘米|mm|毫米|meter|meters|centimeter|centimeters|millimeter|millimeters)?",
        r"span\s*[:=]?\s*(\d+(?:\.\d+)?)\s*(m|cm|mm|meter|meters|centimeter|centimeters|millimeter|millimeters)?",
        r"length\s*[:=]?\s*(\d+(?:\.\d+)?)\s*(m|cm|mm|meter|meters|centimeter|centimeters|millimeter|millimeters)?",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            value = float(match.group(1))
            unit = match.group(2) if match.lastindex >= 2 and match.group(2) else "m"
            return length_to_meters(value, unit)
    return None


def parse_span_ratio(text: str) -> Optional[float]:
    match = re.search(r"(\d+(?:\.\d+)?)\s*倍直径", text)
    if match:
        return float(match.group(1))
    return None


def _parse_diameter_or_radius(text: str) -> tuple[Optional[float], Optional[float]]:
    diameter_m: Optional[float] = None
    radius_m: Optional[float] = None

    diameter_patterns = [
        (r"直径\s*(\d+(?:\.\d+)?)\s*(米|m|cm|厘米|mm|毫米|meter|meters|centimeter|centimeters|millimeter|millimeters)?", None),
        (r"直径\s*(\d+(?:\.\d+)?)\s*(?:cm|厘米)", "cm"),
        (r"diameter\s*(\d+(?:\.\d+)?)\s*(m|cm|mm|meter|meters|centimeter|centimeters|millimeter|millimeters)?", None),
        (r"(\d+(?:\.\d+)?)\s*(?:cm|厘米)\s*的?\s*圆柱", "cm"),
        (r"(\d+(?:\.\d+)?)\s*(?:cm|厘米)\b.*圆柱", "cm"),
        (r"直径\s*(\d+(?:\.\d+)?)\s*(?:cm|厘米)", "cm"),
    ]
    for pattern, default_unit in diameter_patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            value = float(match.group(1))
            unit = match.group(2) if match.lastindex >= 2 and match.group(2) else (default_unit or "m")
            diameter_m = length_to_meters(value, unit)
            break

    radius_patterns = [
        r"半径\s*(\d+(?:\.\d+)?)\s*(米|m|cm|厘米|mm|毫米|meter|meters|centimeter|centimeters|millimeter|millimeters)?",
        r"radius\s*(\d+(?:\.\d+)?)\s*(m|cm|mm|meter|meters|centimeter|centimeters|millimeter|millimeters)?",
    ]
    for pattern in radius_patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            value = float(match.group(1))
            unit = match.group(2) if match.lastindex >= 2 and match.group(2) else "m"
            radius_m = length_to_meters(value, unit)
            break

    if diameter_m is None and radius_m is None:
        length = parse_length(text)
        if length is not None and re.search(r"半径|radius", text, flags=re.IGNORECASE):
            radius_m = length_to_meters(length.value, length.unit)
        elif length is not None and re.search(r"直径|diameter", text, flags=re.IGNORECASE):
            diameter_m = length_to_meters(length.value, length.unit)

    return diameter_m, radius_m


def parse_nl_input(text: str) -> ParsedParams:
    diameter_m, radius_m = _parse_diameter_or_radius(text)
    if diameter_m is None and radius_m is not None:
        diameter_m = 2.0 * radius_m
    elif radius_m is None and diameter_m is not None:
        radius_m = diameter_m / 2.0

    velocity_ms: Optional[float] = None
    velocity = parse_velocity(text)
    if velocity is not None:
        velocity_ms = velocity_to_ms(velocity.value, velocity.unit)

    dimension = parse_dimension(text)
    span_m = parse_span(text)
    span_ratio = parse_span_ratio(text)
    if dimension is None and (span_m is not None or span_ratio is not None):
        dimension = SimulationDimension.THREE_D

    return ParsedParams(
        diameter_m=diameter_m,
        radius_m=radius_m,
        reynolds=parse_reynolds(text),
        velocity_ms=velocity_ms,
        fluid=parse_fluid(text),
        dimension=dimension,
        span_m=span_m if span_m is not None else (
            None if span_ratio is None or diameter_m is None else span_ratio * diameter_m
        ),
    )
