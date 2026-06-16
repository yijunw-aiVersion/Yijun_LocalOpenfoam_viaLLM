"""Tests for OpenFOAM case generation."""

from __future__ import annotations

from pathlib import Path

import pytest

from cfd_workflow.models import CompleteParams, FluidType, SimulationDimension
from cfd_workflow.openfoam.case_generator import (
    DEFAULT_MAX_ITERATIONS,
    build_case_config,
    compute_write_interval,
    render_case,
    solver_settings,
)
from cfd_workflow.openfoam.monitor import DEFAULT_RESIDUAL_TOL


@pytest.mark.parametrize(
    "max_iterations,expected_write_interval",
    [
        (200, 10),
        (500, 10),
        (4, 1),
        (1, 1),
    ],
)
def test_compute_write_interval(max_iterations: int, expected_write_interval: int):
    assert compute_write_interval(max_iterations) == expected_write_interval


def test_solver_settings_default():
    assert solver_settings() == {
        "max_iterations": DEFAULT_MAX_ITERATIONS,
        "write_interval": 10,
    }


def test_build_case_config():
    params = CompleteParams(
        diameter_m=0.1,
        reynolds=100.0,
        velocity_ms=1.0,
        fluid=FluidType.AIR,
        kinematic_viscosity_m2s=0.001,
        density_kgm3=1.225,
    )
    config = build_case_config(params, max_iterations=200)
    assert config["geometry"]["diameter_m"] == 0.1
    assert config["solver"]["name"] == "simpleFoam"
    assert config["solver"]["max_iterations"] == 200
    assert config["mesh"]["background"] == "blockMesh"
    assert config["solver"]["convergence_tolerance"] == DEFAULT_RESIDUAL_TOL
    assert "1.0 0 0" in config["boundary_conditions"]["inlet"]["U"]


def test_build_case_config_custom_residual_tol():
    params = CompleteParams(
        diameter_m=0.1,
        reynolds=100.0,
        velocity_ms=1.0,
        fluid=FluidType.AIR,
        kinematic_viscosity_m2s=0.001,
        density_kgm3=1.225,
    )
    config = build_case_config(params, residual_tol=1e-6)
    assert config["solver"]["convergence_tolerance"] == 1e-6


def test_render_case_3d_coarse_mesh(tmp_path: Path):
    params = CompleteParams(
        diameter_m=0.1,
        reynolds=100.0,
        velocity_ms=1.0,
        fluid=FluidType.AIR,
        kinematic_viscosity_m2s=0.001,
        density_kgm3=1.225,
        dimension=SimulationDimension.THREE_D,
        span_m=1.0,
    )
    case_dir = render_case(params, tmp_path / "case3d_coarse", coarse=True)
    block = (case_dir / "system" / "blockMeshDict").read_text(encoding="utf-8")
    assert "20 14 5" in block


def test_render_case_3d_uses_z_patches(tmp_path: Path):
    params = CompleteParams(
        diameter_m=0.1,
        reynolds=100.0,
        velocity_ms=1.0,
        fluid=FluidType.AIR,
        kinematic_viscosity_m2s=0.001,
        density_kgm3=1.225,
        dimension=SimulationDimension.THREE_D,
        span_m=1.0,
    )
    case_dir = render_case(params, tmp_path / "case3d")
    block = (case_dir / "system" / "blockMeshDict").read_text(encoding="utf-8")
    u_field = (case_dir / "0" / "U").read_text(encoding="utf-8")
    assert "zMin" in block
    assert "zMax" in block
    assert "frontAndBack" not in block
    assert "(40 30" in block or "(40 30 " in block
    assert "zMin" in u_field
    assert "empty" not in u_field


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
    assert "writeInterval   10;" in control_dict
