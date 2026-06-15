"""OpenFOAM case generation for 2D cylinder flow."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from cfd_workflow.models import CompleteParams

DEFAULT_MAX_ITERATIONS = 200

REQUIRED_CASE_FILES = [
    "system/blockMeshDict",
    "system/snappyHexMeshDict",
    "system/controlDict",
    "system/fvSchemes",
    "system/fvSolution",
    "constant/transportProperties",
    "constant/turbulenceProperties",
    "constant/triSurface/cylinder.stl",
    "0/U",
    "0/p",
    "Allrun",
]


def compute_domain_size(diameter_m: float) -> dict[str, float]:
    """Return mesh domain extents in meters (2D channel around cylinder)."""
    r = diameter_m / 2.0
    return {
        "radius": r,
        "x_up": 10.0 * r,
        "x_down": 25.0 * r,
        "y_half": 10.0 * r,
        "z_half": 0.01,
    }


def compute_nu_from_params(params: CompleteParams) -> float:
    """Kinematic viscosity consistent with Re, U, and D."""
    return params.velocity_ms * params.diameter_m / params.reynolds


def compute_write_interval(max_iterations: int) -> int:
    """OpenFOAM writeInterval — frequent enough for early-stop post-processing."""
    return max(1, min(10, max_iterations // 4))


def _template_context(params: CompleteParams, max_iterations: int = DEFAULT_MAX_ITERATIONS) -> dict:
    domain = compute_domain_size(params.diameter_m)
    r = domain["radius"]
    nu = compute_nu_from_params(params)
    x_min = -domain["x_up"]
    x_max = domain["x_down"]
    y_min = -domain["y_half"]
    y_max = domain["y_half"]
    return {
        **domain,
        "diameter": params.diameter_m,
        "velocity": params.velocity_ms,
        "reynolds": params.reynolds,
        "nu": nu,
        "rho": params.density_kgm3,
        "fluid": params.fluid.value,
        "x_min": x_min,
        "x_max": x_max,
        "y_min": y_min,
        "y_max": y_max,
        "seed_x": 3.0 * r,
        "seed_y": 0.0,
        "nx": 60,
        "ny": 40,
        "end_time": max_iterations,
        "write_interval": compute_write_interval(max_iterations),
    }


def solver_settings(max_iterations: int = DEFAULT_MAX_ITERATIONS) -> dict[str, int]:
    """Return solver iteration settings for reports and metadata."""
    return {
        "max_iterations": max_iterations,
        "write_interval": compute_write_interval(max_iterations),
    }


def build_case_config(
    params: CompleteParams,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
    residual_tol: float | None = None,
) -> dict:
    """Structured summary of the OpenFOAM case (problem_description §2)."""
    from cfd_workflow.openfoam.monitor import DEFAULT_RESIDUAL_TOL

    tol = residual_tol if residual_tol is not None else DEFAULT_RESIDUAL_TOL
    ctx = _template_context(params, max_iterations=max_iterations)
    solver = solver_settings(max_iterations)
    return {
        "geometry": {
            "type": "2D cylinder (empty front/back)",
            "diameter_m": params.diameter_m,
            "radius_m": ctx["radius"],
            "domain_m": {
                "x_min": ctx["x_min"],
                "x_max": ctx["x_max"],
                "y_min": ctx["y_min"],
                "y_max": ctx["y_max"],
                "z_half": ctx["z_half"],
            },
        },
        "mesh": {
            "background": "blockMesh",
            "refinement": "snappyHexMesh",
            "background_cells": {"nx": ctx["nx"], "ny": ctx["ny"]},
            "surface": "constant/triSurface/cylinder.stl",
        },
        "boundary_conditions": {
            "inlet": {"U": f"({params.velocity_ms} 0 0) m/s"},
            "outlet": {"p": "fixedValue 0"},
            "cylinder": {"U": "noSlip"},
            "top_bottom": {"U": "slip"},
        },
        "fluid": {
            "name": params.fluid.value,
            "density_kgm3": params.density_kgm3,
            "kinematic_viscosity_m2s": ctx["nu"],
            "reynolds": params.reynolds,
        },
        "solver": {
            "name": "simpleFoam",
            "turbulence": "laminar",
            "max_iterations": solver["max_iterations"],
            "write_interval": solver["write_interval"],
            "convergence_tolerance": tol,
        },
    }


def write_cylinder_stl(output_dir: Path, radius: float, height: float = 0.02) -> Path:
    """Write cylinder STL for snappyHexMesh."""
    import pyvista as pv

    surf_dir = Path(output_dir) / "constant" / "triSurface"
    surf_dir.mkdir(parents=True, exist_ok=True)
    stl_path = surf_dir / "cylinder.stl"
    cyl = pv.Cylinder(
        center=(0.0, 0.0, 0.0),
        direction=(0.0, 0.0, 1.0),
        radius=radius,
        height=height,
        resolution=48,
    )
    cyl.triangulate().save(str(stl_path))
    return stl_path


def _templates_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "templates" / "cylinder_2d"


def render_case(
    params: CompleteParams,
    output_dir: Path,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
) -> Path:
    """Render OpenFOAM case templates into output_dir."""
    output_dir = Path(output_dir)
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    env = Environment(
        loader=FileSystemLoader(str(_templates_dir())),
        autoescape=select_autoescape(enabled_extensions=()),
        keep_trailing_newline=True,
    )

    template_map = {
        "system/blockMeshDict.j2": "system/blockMeshDict",
        "system/snappyHexMeshDict.j2": "system/snappyHexMeshDict",
        "system/controlDict.j2": "system/controlDict",
        "system/fvSchemes.j2": "system/fvSchemes",
        "system/fvSolution.j2": "system/fvSolution",
        "constant/transportProperties.j2": "constant/transportProperties",
        "constant/turbulenceProperties.j2": "constant/turbulenceProperties",
        "0/U.j2": "0/U",
        "0/p.j2": "0/p",
        "Allrun.j2": "Allrun",
    }

    ctx = _template_context(params, max_iterations=max_iterations)
    for src, dst in template_map.items():
        target = output_dir / dst
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(env.get_template(src).render(**ctx), encoding="utf-8")

    write_cylinder_stl(output_dir, radius=ctx["radius"])

    (output_dir / "constant" / "polyMesh").mkdir(parents=True, exist_ok=True)
    meta = output_dir / "case_meta.json"
    meta.write_text(
        json.dumps(
            {
                "prompt_params": params.model_dump(),
                "solver": solver_settings(max_iterations),
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return output_dir


def validate_case(output_dir: Path) -> list[str]:
    """Return list of missing required files."""
    output_dir = Path(output_dir)
    missing = [rel for rel in REQUIRED_CASE_FILES if not (output_dir / rel).exists()]
    return missing
