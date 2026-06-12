"""Simulation stage agent — blockMesh through foamToVTK."""

from __future__ import annotations

from cfd_workflow.agents.base import StageAgent
from cfd_workflow.agents.state import WorkflowState
from cfd_workflow.openfoam.docker_runner import docker_available, run_simulation_docker
from cfd_workflow.openfoam.runner import (
    is_converged,
    openfoam_available,
    parse_residuals,
    run_simulation,
)


class SimulationAgent(StageAgent):
    name = "simulation_agent"
    role = "OpenFOAM Simulation Runner"

    def _run(self, state: WorkflowState) -> tuple[str, str]:
        if state.case_dir is None:
            state.report["status"] = "simulation_failed"
            msg = "No case directory available for simulation"
            state.report.setdefault("issues", []).append(msg)
            return "failed", msg

        can_run_local = openfoam_available()
        can_run_docker = state.use_docker and docker_available()

        if not can_run_local and not can_run_docker:
            if state.use_docker and not docker_available():
                state.report["status"] = "blocked"
                msg = (
                    "Docker requested but CLI not available. Install colima + docker-cli "
                    "(conda install -c conda-forge colima docker-cli) and run colima start."
                )
            else:
                state.report["status"] = "blocked"
                msg = "OpenFOAM not installed. Re-run with --docker or install OpenFOAM locally."
            state.report.setdefault("issues", []).append(msg)
            return "blocked", msg

        try:
            if can_run_docker:
                state.report["execution_mode"] = "docker"
                step_results = run_simulation_docker(state.case_dir, on_line=state.on_line)
            else:
                state.report["execution_mode"] = "local"
                step_results = run_simulation(state.case_dir, on_line=state.on_line)

            state.report["simulation_steps"] = [
                {"command": r.command, "success": r.success, "log": str(r.log_file)}
                for r in step_results
            ]

            if not all(r.success for r in step_results):
                state.report["status"] = "simulation_failed"
                failed = next(r for r in step_results if not r.success)
                msg = f"Command failed: {failed.command} (see {failed.log_file})"
                state.report.setdefault("issues", []).append(msg)
                return "failed", msg

            log_path = state.case_dir / "log.simpleFoam"
            if log_path.exists():
                residuals = parse_residuals(log_path.read_text(encoding="utf-8", errors="replace"))
                state.report["residuals"] = residuals
                state.report["converged"] = is_converged(residuals)

            return "success", f"Simulation completed via {state.report.get('execution_mode', 'unknown')}"

        except Exception as exc:  # noqa: BLE001
            state.report["status"] = "simulation_failed"
            state.report.setdefault("issues", []).append(str(exc))
            return "error", str(exc)
