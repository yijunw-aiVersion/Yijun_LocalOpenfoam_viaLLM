"""OpenFOAM command execution."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional


@dataclass
class StepResult:
    command: str
    returncode: int
    log_file: Path
    success: bool


@dataclass
class SimulationProgress:
    step: str = ""
    status: str = "pending"
    residuals: dict[str, float] = field(default_factory=dict)
    converged: bool = False


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
            if on_line:
                on_line(line.rstrip())
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
) -> list[StepResult]:
    case_dir = Path(case_dir)
    bashrc = find_openfoam_env()
    if not shutil.which("blockMesh") and bashrc is None:
        raise RuntimeError(
            "OpenFOAM not found. Install OpenFOAM and source its bashrc, "
            "or set WM_PROJECT_DIR so blockMesh/simpleFoam are on PATH."
        )

    steps = [
        ("blockMesh", "log.blockMesh"),
        ("snappyHexMesh -overwrite", "log.snappyHexMesh"),
        ("simpleFoam", "log.simpleFoam"),
        ("foamToVTK -latestTime", "log.foamToVTK"),
    ]
    results: list[StepResult] = []
    for cmd, log_name in steps:
        if on_line:
            on_line(f"=== Running: {cmd} ===")
        result = run_command(cmd, case_dir, log_name, on_line=on_line, bashrc=bashrc)
        results.append(result)
        if not result.success:
            break
    return results


def parse_residuals(log_text: str) -> dict[str, float]:
    """Parse final residual values from simpleFoam log."""
    residuals: dict[str, float] = {}
    patterns = {
        "U": r"Solving for U[^,]*,\s*Initial residual\s*=\s*([\d.eE+-]+)",
        "p": r"Solving for p[^,]*,\s*Initial residual\s*=\s*([\d.eE+-]+)",
    }
    for field_name, pattern in patterns.items():
        matches = re.findall(pattern, log_text)
        if matches:
            residuals[field_name] = float(matches[-1])
    return residuals


def is_converged(residuals: dict[str, float], tol: float = 1e-4) -> bool:
    if not residuals:
        return False
    return all(value <= tol for value in residuals.values())
