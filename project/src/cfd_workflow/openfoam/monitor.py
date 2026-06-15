"""OpenFOAM simulation log monitoring and case-setup summaries."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

DEFAULT_RESIDUAL_TOL = 1e-4

_TIME_RE = re.compile(r"^\s*Time\s*=\s*(\d+)")
_RESIDUAL_PATTERNS = {
    "U": re.compile(r"Solving for U[^,]*,\s*Initial residual\s*=\s*([\d.eE+-]+)"),
    "p": re.compile(r"Solving for p[^,]*,\s*Initial residual\s*=\s*([\d.eE+-]+)"),
}


@dataclass
class SimulationProgress:
    step: str = ""
    status: str = "pending"
    iteration: int = 0
    max_iterations: int = 0
    residuals: dict[str, float] = field(default_factory=dict)
    converged: bool = False


def parse_residuals(log_text: str) -> dict[str, float]:
    """Parse final residual values from a simpleFoam log."""
    residuals: dict[str, float] = {}
    for field_name, pattern in _RESIDUAL_PATTERNS.items():
        matches = pattern.findall(log_text)
        if matches:
            residuals[field_name] = float(matches[-1])
    return residuals


def is_converged(residuals: dict[str, float], tol: float = DEFAULT_RESIDUAL_TOL) -> bool:
    if not residuals:
        return False
    return all(value <= tol for value in residuals.values())


def update_progress_from_line(progress: SimulationProgress, line: str) -> bool:
    """Update progress from one log line. Returns True when iteration advances."""
    changed = False
    time_match = _TIME_RE.search(line)
    if time_match:
        progress.iteration = int(time_match.group(1))
        changed = True

    for field_name, pattern in _RESIDUAL_PATTERNS.items():
        match = pattern.search(line)
        if match:
            progress.residuals[field_name] = float(match.group(1))

    progress.converged = is_converged(progress.residuals)
    return changed


def format_progress_summary(progress: SimulationProgress) -> str:
    """One-line solver progress for CLI streaming."""
    residual_parts = ", ".join(
        f"{name}={value:.2e}" for name, value in sorted(progress.residuals.items())
    )
    if not residual_parts:
        residual_parts = "residuals pending"

    max_iter = progress.max_iterations or "?"
    state = "converged" if progress.converged else progress.status or "running"
    return (
        f"[{progress.step or 'solver'}] "
        f"iteration {progress.iteration}/{max_iter} — {residual_parts} — {state}"
    )


def format_case_setup_lines(config: dict[str, Any]) -> list[str]:
    """Human-readable lines describing the generated OpenFOAM case."""
    geom = config["geometry"]
    mesh = config["mesh"]
    bc = config["boundary_conditions"]
    fluid = config["fluid"]
    solver = config["solver"]

    domain = geom["domain_m"]
    lines = [
        "=== OpenFOAM case configuration ===",
        (
            f"Geometry: {geom['type']}, D={geom['diameter_m']} m, "
            f"domain x=[{domain['x_min']}, {domain['x_max']}] m, "
            f"y=[{domain['y_min']}, {domain['y_max']}] m"
        ),
        (
            f"Mesh: {mesh['background']} background "
            f"({mesh['background_cells']['nx']}×{mesh['background_cells']['ny']}) "
            f"+ {mesh['refinement']} around cylinder STL"
        ),
        (
            f"Boundaries: inlet U={bc['inlet']['U']}, "
            f"outlet p={bc['outlet']['p']}, cylinder={bc['cylinder']['U']}"
        ),
        (
            f"Fluid: {fluid['name']}, rho={fluid['density_kgm3']} kg/m³, "
            f"nu={fluid['kinematic_viscosity_m2s']:.6g} m²/s (Re={fluid['reynolds']})"
        ),
        (
            f"Solver: {solver['name']} ({solver['turbulence']}), "
            f"max_iterations={solver['max_iterations']}, "
            f"write_interval={solver['write_interval']}, "
            f"residual_tol={solver['convergence_tolerance']}"
        ),
        "=================================",
    ]
    return lines
