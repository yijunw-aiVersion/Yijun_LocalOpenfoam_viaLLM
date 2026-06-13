"""Tests for OpenFOAM case generation."""

from __future__ import annotations

from pathlib import Path

import pytest

from cfd_workflow.models import CompleteParams, FluidType
from cfd_workflow.openfoam.case_generator import (
    DEFAULT_MAX_ITERATIONS,
    compute_write_interval,
    render_case,
    solver_settings,
)


@pytest.mark.parametrize(
    "max_iterations,expected_write_interval",
    [
        (200, 50),
        (500, 125),
        (4, 1),
        (1, 1),
    ],
)
def test_compute_write_interval(max_iterations: int, expected_write_interval: int):
    assert compute_write_interval(max_iterations) == expected_write_interval


def test_solver_settings_default():
    assert solver_settings() == {
        "max_iterations": DEFAULT_MAX_ITERATIONS,
        "write_interval": 50,
    }


def test_render_case_respects_max_iterations(tmp_path: Path):
    params = CompleteParams(
        diameter_m=0.1,
        reynolds=100.0,
        velocity_ms=1.0,
        fluid=FluidType.AIR,
        kinematic_viscosity_m2s=0.001,
        density_kgm3=1.225,
    )
    case_dir = render_case(params, tmp_path / "case", max_iterations=500)
    control_dict = (case_dir / "system" / "controlDict").read_text(encoding="utf-8")
    assert "endTime         500;" in control_dict
    assert "writeInterval   125;" in control_dict
