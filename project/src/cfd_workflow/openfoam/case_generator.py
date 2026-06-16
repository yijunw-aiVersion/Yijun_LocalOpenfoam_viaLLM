"""OpenFOAM case generation for 2D and 3D cylinder flow."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from cfd_workflow.models import CompleteParams, SimulationDimension

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

_TEMPLATE_MAP = {
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


def compute_nz(span_m: float, diameter_m: float, *, coarse: bool = False) -> int:
    """Coarse z resolution for 3D prototype meshes."""
    if coarse:
        return 5
    ratio = span_m / diameter_m if diameter_m > 0 else 10.0
    return max(8, min(16, int(6 + ratio)))


def compute_mesh_settings(params: CompleteParams, *, coarse: bool = False) -> dict[str, float | int]:
    """Return domain extents and background mesh counts."""
    r = params.diameter_m / 2.0
    settings: dict[str, float | int] = {
        "radius": r,
        "x_up": 10.0 * r,
        "x_down": 25.0 * r,
        "y_half": 10.0 * r,
        "x_min": -10.0 * r,
        "x_max": 25.0 * r,
        "y_min": -10.0 * r,
        "y_max": 10.0 * r,
        "seed_x": 3.0 * r,
        "seed_y": 0.0,
        "coarse_mesh": coarse,
    }
    if params.dimension == SimulationDimension.THREE_D:
        span_m = params.span_m or (10.0 * params.diameter_m)
        if coarse:
            nx, ny = 20, 14
            snappy_levels = (1, 2)
            max_global_cells = 120000
        else:
            nx, ny = 40, 30
            snappy_levels = (2, 3)
            max_global_cells = 400000
        settings.update(
            {
                "span_m": span_m,
                "z_half": span_m / 2.0,
                "nz": compute_nz(span_m, params.diameter_m, coarse=coarse),
                "nx": nx,
                "ny": ny,
                "cylinder_height": span_m,
                "snappy_refine_min": snappy_levels[0],
                "snappy_refine_max": snappy_levels[1],
                "max_global_cells": max_global_cells,
            }
        )
    else:
        settings.update(
            {
                "span_m": 0.02,
                "z_half": 0.01,
                "nz": 1,
                "nx": 60,
                "ny": 40,
                "cylinder_height": 0.02,
                "snappy_refine_min": 2,
                "snappy_refine_max": 3,
                "max_global_cells": 200000,
            }
        )
    return settings


def resolve_coarse_mesh(
    params: CompleteParams,
    *,
    coarse_mesh: bool = False,
    fine_mesh: bool = False,
) -> bool:
    """3D runs default to a coarse background mesh unless --fine-mesh is set."""
    if coarse_mesh:
        return True
    if fine_mesh:
        return False
    return params.dimension == SimulationDimension.THREE_D


def compute_domain_size(diameter_m: float) -> dict[str, float]:
    """Return 2D mesh domain extents (backward-compatible helper)."""
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


def _template_context(
    params: CompleteParams,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
    *,
    coarse: bool = False,
) -> dict:
    mesh = compute_mesh_settings(params, coarse=coarse)
    nu = compute_nu_from_params(params)
    return {
        **mesh,
        "diameter": params.diameter_m,
        "velocity": params.velocity_ms,
        "reynolds": params.reynolds,
        "nu": nu,
        "rho": params.density_kgm3,
        "fluid": params.fluid.value,
        "dimension": params.dimension.value,
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
    *,
    coarse: bool = False,
) -> dict:
    """Structured summary of the OpenFOAM case (problem_description §2)."""
    from cfd_workflow.openfoam.monitor import DEFAULT_RESIDUAL_TOL

    tol = residual_tol if residual_tol is not None else DEFAULT_RESIDUAL_TOL
    ctx = _template_context(params, max_iterations=max_iterations, coarse=coarse)
    solver = solver_settings(max_iterations)
    is_3d = params.dimension == SimulationDimension.THREE_D

    geometry_type = (
        "3D finite cylinder (span along z)"
        if is_3d
        else "2D cylinder (empty front/back)"
    )
    domain = {
        "x_min": ctx["x_min"],
        "x_max": ctx["x_max"],
        "y_min": ctx["y_min"],
        "y_max": ctx["y_max"],
        "z_half": ctx["z_half"],
    }
    if is_3d:
        domain["span_m"] = ctx["span_m"]
        domain["span_ratio"] = params.span_ratio

    mesh_cells = {"nx": ctx["nx"], "ny": ctx["ny"]}
    if is_3d:
        mesh_cells["nz"] = ctx["nz"]

    boundary_conditions = {
        "inlet": {"U": f"({params.velocity_ms} 0 0) m/s"},
        "outlet": {"p": "fixedValue 0"},
        "cylinder": {"U": "noSlip"},
        "top_bottom": {"U": "slip"},
    }
    if is_3d:
        boundary_conditions["zMin_zMax"] = {"U": "slip", "p": "zeroGradient"}

    return {
        "dimension": params.dimension.value,
        "geometry": {
            "type": geometry_type,
            "diameter_m": params.diameter_m,
            "radius_m": ctx["radius"],
            "domain_m": domain,
        },
        "mesh": {
            "background": "blockMesh",
            "refinement": "snappyHexMesh",
            "background_cells": mesh_cells,
            "surface": "constant/triSurface/cylinder.stl",
            "coarse": coarse,
        },
        "boundary_conditions": boundary_conditions,
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


def write_cylinder_stl(output_dir: Path, radius: float, height: float) -> Path:
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


def _templates_dir(dimension: SimulationDimension) -> Path:
    folder = "cylinder_3d" if dimension == SimulationDimension.THREE_D else "cylinder_2d"
    return Path(__file__).resolve().parents[3] / "templates" / folder


def render_case(
    params: CompleteParams,
    output_dir: Path,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
    *,
    coarse: bool = False,
) -> Path:
    """Render OpenFOAM case templates into output_dir."""
    output_dir = Path(output_dir)
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    env = Environment(
        loader=FileSystemLoader(str(_templates_dir(params.dimension))),
        autoescape=select_autoescape(enabled_extensions=()),
        keep_trailing_newline=True,
    )

    ctx = _template_context(params, max_iterations=max_iterations, coarse=coarse)
    for src, dst in _TEMPLATE_MAP.items():
        target = output_dir / dst
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(env.get_template(src).render(**ctx), encoding="utf-8")

    write_cylinder_stl(output_dir, radius=float(ctx["radius"]), height=float(ctx["cylinder_height"]))

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
