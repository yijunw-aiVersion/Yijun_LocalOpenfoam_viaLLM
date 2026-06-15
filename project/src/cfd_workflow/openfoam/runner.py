"""OpenFOAM command execution."""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from cfd_workflow.openfoam.case_generator import DEFAULT_MAX_ITERATIONS
from cfd_workflow.openfoam.monitor import (
    SimulationProgress,
    format_progress_summary,
    is_converged,
    parse_residuals,
    update_progress_from_line,
)


@dataclass
class StepResult:
    command: str
    returncode: int
    log_file: Path
    success: bool


def find_openfoam_env() -> Optional[Path]:
    """Return bashrc path if OpenFOAM installation is detected."""
    wm_dir = os.environ.get("WM_PROJECT_DIR")
    if wm_dir:
        bashrc = Path(wm_dir) / "etc" / "bashrc"
        if bashrc.exists():
            return bashrc

    candidates = [
        Path("/opt/openfoam2312/etc/bashrc"),
        Path("/opt/openfoam2406/etc/bashrc"),
        Path("/usr/lib/openfoam/openfoam2312/etc/bashrc"),
        Path.home() / "OpenFOAM" / "OpenFOAM-v2312" / "etc" / "bashrc",
    ]
    for bashrc in candidates:
        if bashrc.exists():
            return bashrc
    return None


def openfoam_available() -> bool:
    return shutil.which("blockMesh") is not None or find_openfoam_env() is not None


def run_command(
    cmd: str,
    cwd: Path,
    log_name: str,
    on_line: Optional[Callable[[str], None]] = None,
    bashrc: Optional[Path] = None,
    on_solver_line: Optional[Callable[[str], None]] = None,
) -> StepResult:
    cwd = Path(cwd)
    log_file = cwd / log_name
    if bashrc:
        shell_cmd = f'source "{bashrc}" && cd "{cwd}" && {cmd}'
    else:
        shell_cmd = f'cd "{cwd}" && {cmd}'

    with log_file.open("w", encoding="utf-8") as log:
        proc = subprocess.Popen(
            shell_cmd,
            shell=True,
            executable="/bin/bash",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            log.write(line)
            stripped = line.rstrip()
            if on_line:
                on_line(stripped)
            if on_solver_line:
                on_solver_line(stripped)
        proc.wait()

    return StepResult(
        command=cmd,
        returncode=proc.returncode,
        log_file=log_file,
        success=proc.returncode == 0,
    )


def run_simulation(
    case_dir: Path,
    on_line: Optional[Callable[[str], None]] = None,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
    progress: Optional[SimulationProgress] = None,
) -> tuple[list[StepResult], SimulationProgress]:
    case_dir = Path(case_dir)
    bashrc = find_openfoam_env()
    if not shutil.which("blockMesh") and bashrc is None:
        raise RuntimeError(
            "OpenFOAM not found. Install OpenFOAM and source its bashrc, "
            "or set WM_PROJECT_DIR so blockMesh/simpleFoam are on PATH."
        )

    sim_progress = progress or SimulationProgress(max_iterations=max_iterations)
    steps = [
        ("blockMesh", "log.blockMesh"),
        ("snappyHexMesh -overwrite", "log.snappyHexMesh"),
        ("simpleFoam", "log.simpleFoam"),
        ("foamToVTK -latestTime", "log.foamToVTK"),
    ]
    results: list[StepResult] = []
    for cmd, log_name in steps:
        sim_progress.step = cmd.split()[0]
        sim_progress.status = "running"
        if on_line:
            on_line(f"=== {cmd} ===")

        solver_line_cb: Optional[Callable[[str], None]] = None
        if cmd == "simpleFoam":

            def _on_solver_line(line: str, *, _progress: SimulationProgress = sim_progress) -> None:
                if update_progress_from_line(_progress, line) and on_line:
                    on_line(format_progress_summary(_progress))

            solver_line_cb = _on_solver_line

        result = run_command(
            cmd,
            case_dir,
            log_name,
            on_line=on_line if cmd != "simpleFoam" else None,
            bashrc=bashrc,
            on_solver_line=solver_line_cb,
        )
        results.append(result)
        if not result.success:
            sim_progress.status = "failed"
            break
    else:
        sim_progress.status = "completed"

    log_path = case_dir / "log.simpleFoam"
    if log_path.exists():
        sim_progress.residuals = parse_residuals(
            log_path.read_text(encoding="utf-8", errors="replace")
        )
        sim_progress.converged = is_converged(sim_progress.residuals)

    if on_line and sim_progress.step == "simpleFoam":
        on_line(format_progress_summary(sim_progress))

    return results, sim_progress
