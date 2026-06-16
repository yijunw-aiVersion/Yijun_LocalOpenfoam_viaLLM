"""Run OpenFOAM simulations inside Docker."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Callable, Optional

from cfd_workflow.openfoam.case_generator import DEFAULT_MAX_ITERATIONS
from cfd_workflow.openfoam.monitor import (
    DEFAULT_RESIDUAL_TOL,
    SimulationProgress,
    format_progress_summary,
    is_converged,
    parse_residuals,
    simplefoam_stream_handlers,
)
from cfd_workflow.openfoam.runner import StepResult, _terminate_process

DEFAULT_IMAGE = "opencfd/openfoam-default:2412"


def docker_available() -> bool:
    return shutil.which("docker") is not None


def _docker_env() -> dict[str, str]:
    env = os.environ.copy()
    colima_sock = Path.home() / ".colima" / "default" / "docker.sock"
    if colima_sock.exists() and not env.get("DOCKER_HOST"):
        env["DOCKER_HOST"] = f"unix://{colima_sock}"
    return env


def _log_success(log_file: Path) -> bool:
    if not log_file.exists() or log_file.stat().st_size == 0:
        return False
    text = log_file.read_text(encoding="utf-8", errors="replace")
    return "FOAM FATAL ERROR" not in text


def _image_exists_locally(image: str) -> bool:
    proc = subprocess.run(
        ["docker", "image", "inspect", image],
        env=_docker_env(),
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0


def ensure_image(image: str = DEFAULT_IMAGE, on_line: Optional[Callable[[str], None]] = None) -> None:
    if _image_exists_locally(image):
        if on_line:
            on_line(f"Using local Docker image: {image}")
        return
    if on_line:
        on_line(f"Pulling Docker image: {image}")
    proc = subprocess.run(
        ["docker", "pull", image],
        env=_docker_env(),
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"docker pull failed:\n{proc.stdout}\n{proc.stderr}")


def _run_docker_step(
    case_dir: Path,
    image: str,
    cmd: str,
    log_name: str,
    on_line: Optional[Callable[[str], None]] = None,
    on_solver_line: Optional[Callable[[str], None]] = None,
    stop_when: Optional[Callable[[], bool]] = None,
) -> StepResult:
    inner = f"cd /case && {cmd}"
    docker_cmd = [
        "docker",
        "run",
        "--rm",
        "--platform",
        "linux/amd64",
        "-v",
        f"{case_dir}:/case",
        "-w",
        "/case",
        image,
        "bash",
        "-c",
        inner,
    ]
    log_file = case_dir / log_name
    stopped_early = False
    with log_file.open("w", encoding="utf-8") as log:
        proc = subprocess.Popen(
            docker_cmd,
            env=_docker_env(),
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
            if stop_when and stop_when():
                stopped_early = True
                _terminate_process(proc)
                break
        else:
            proc.wait()

    success = (proc.returncode == 0 or stopped_early) and _log_success(log_file)
    return StepResult(
        command=f"docker: {cmd}",
        returncode=0 if success else 1,
        log_file=log_file,
        success=success,
        stopped_early=stopped_early,
    )


def run_simulation_docker(
    case_dir: Path,
    image: str = DEFAULT_IMAGE,
    on_line: Optional[Callable[[str], None]] = None,
    pull: bool = True,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
    residual_tol: float = DEFAULT_RESIDUAL_TOL,
    progress: Optional[SimulationProgress] = None,
) -> tuple[list[StepResult], SimulationProgress]:
    """Run blockMesh → snappyHexMesh → simpleFoam → foamToVTK, one Docker step at a time."""
    case_dir = Path(case_dir).resolve()
    if not docker_available():
        raise RuntimeError(
            "Docker CLI not found. Install via: "
            "conda install -n cfd-agent-test -c conda-forge colima docker-cli && colima start"
        )

    if pull:
        ensure_image(image, on_line=on_line)

    sim_progress = progress or SimulationProgress(
        max_iterations=max_iterations,
        residual_tol=residual_tol,
    )
    sim_progress.residual_tol = residual_tol
    steps = [
        ("blockMesh", "log.blockMesh"),
        ("snappyHexMesh -overwrite", "log.snappyHexMesh"),
        ("simpleFoam", "log.simpleFoam"),
        ("foamToVTK -latestTime", "log.foamToVTK"),
    ]

    if on_line:
        on_line("=== Docker: starting OpenFOAM container ===")

    results: list[StepResult] = []
    for cmd, log_name in steps:
        sim_progress.step = cmd.split()[0]
        sim_progress.status = "running"
        if on_line:
            on_line(f"=== {cmd} ===")

        solver_line_cb: Optional[Callable[[str], None]] = None
        stop_when_cb: Optional[Callable[[], bool]] = None
        if cmd == "simpleFoam":
            solver_line_cb, stop_when_cb = simplefoam_stream_handlers(sim_progress, on_line)

        result = _run_docker_step(
            case_dir,
            image,
            cmd,
            log_name,
            on_line=on_line if cmd != "simpleFoam" else None,
            on_solver_line=solver_line_cb,
            stop_when=stop_when_cb,
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
        sim_progress.converged = is_converged(sim_progress.residuals, tol=sim_progress.residual_tol)

    if on_line and sim_progress.step == "simpleFoam":
        on_line(format_progress_summary(sim_progress))

    return results, sim_progress
