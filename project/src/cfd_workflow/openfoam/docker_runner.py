"""Run OpenFOAM simulations inside Docker."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Callable, Optional

from cfd_workflow.openfoam.runner import StepResult

DEFAULT_IMAGE = "opencfd/openfoam-default:2412"


def docker_available() -> bool:
    return shutil.which("docker") is not None


def _docker_env() -> dict[str, str]:
    env = os.environ.copy()
    colima_sock = Path.home() / ".colima" / "default" / "docker.sock"
    if colima_sock.exists() and not env.get("DOCKER_HOST"):
        env["DOCKER_HOST"] = f"unix://{colima_sock}"
    return env


def _docker_shell_script(steps: list[tuple[str, str]]) -> str:
    """Build bash script for OpenFOAM commands inside the container."""
    lines = [
        "set -e",
        "cd /case",
    ]
    for cmd, log_name in steps:
        lines.append(f'echo "=== {cmd} ==="')
        lines.append(f"{cmd} > {log_name} 2>&1")
    return "\n".join(lines)


def _log_success(log_file: Path) -> bool:
    if not log_file.exists() or log_file.stat().st_size == 0:
        return False
    text = log_file.read_text(encoding="utf-8", errors="replace")
    return "FOAM FATAL ERROR" not in text


def ensure_image(image: str = DEFAULT_IMAGE, on_line: Optional[Callable[[str], None]] = None) -> None:
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


def run_simulation_docker(
    case_dir: Path,
    image: str = DEFAULT_IMAGE,
    on_line: Optional[Callable[[str], None]] = None,
    pull: bool = True,
) -> list[StepResult]:
    """Run blockMesh → snappyHexMesh → simpleFoam → foamToVTK in one Docker container."""
    case_dir = Path(case_dir).resolve()
    if not docker_available():
        raise RuntimeError(
            "Docker CLI not found. Install via: "
            "conda install -n cfd-agent-test -c conda-forge colima docker-cli && colima start"
        )

    if pull:
        ensure_image(image, on_line=on_line)

    steps = [
        ("blockMesh", "log.blockMesh"),
        ("snappyHexMesh -overwrite", "log.snappyHexMesh"),
        ("simpleFoam", "log.simpleFoam"),
        ("foamToVTK -latestTime", "log.foamToVTK"),
    ]

    if on_line:
        on_line("=== Docker: starting OpenFOAM container ===")

    inner = _docker_shell_script(steps)

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

    combined_log = case_dir / "log.docker"
    proc = subprocess.run(
        docker_cmd,
        env=_docker_env(),
        capture_output=True,
        text=True,
    )
    combined_log.write_text(proc.stdout + proc.stderr, encoding="utf-8")
    if on_line:
        for line in (proc.stdout + proc.stderr).splitlines():
            on_line(line)

    results: list[StepResult] = []
    for cmd, log_name in steps:
        log_file = case_dir / log_name
        step_ok = _log_success(log_file)
        results.append(
            StepResult(
                command=f"docker: {cmd}",
                returncode=0 if step_ok else 1,
                log_file=log_file,
                success=step_ok,
            )
        )
        if not step_ok:
            break

    return results
