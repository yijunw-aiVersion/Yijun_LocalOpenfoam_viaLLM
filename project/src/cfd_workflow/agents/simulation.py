"""Simulation stage agent — OpenFOAM execution and progress monitoring."""

from __future__ import annotations

from dataclasses import asdict

from cfd_workflow.agents.base import StageAgent
from cfd_workflow.agents.state import WorkflowState
from cfd_workflow.openfoam.docker_runner import docker_available, run_simulation_docker
from cfd_workflow.openfoam.monitor import SimulationProgress, format_progress_summary
from cfd_workflow.openfoam.runner import openfoam_available, run_simulation


class SimulationAgent(StageAgent):
    name = "simulation_agent"
    role = "OpenFOAM Simulation Runner"

    def _run(self, state: WorkflowState) -> tuple[str, str]:
        if state.dry_run:
            return "skipped", "Dry run — simulation skipped"

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

        progress = SimulationProgress(max_iterations=state.max_iterations)
        try:
            if can_run_docker:
                state.report["execution_mode"] = "docker"
                step_results, progress = run_simulation_docker(
                    state.case_dir,
                    on_line=state.on_line,
                    max_iterations=state.max_iterations,
                    progress=progress,
                )
            else:
                state.report["execution_mode"] = "local"
                step_results, progress = run_simulation(
                    state.case_dir,
                    on_line=state.on_line,
                    max_iterations=state.max_iterations,
                    progress=progress,
                )

            state.report["simulation_steps"] = [
                {"command": r.command, "success": r.success, "log": str(r.log_file)}
                for r in step_results
            ]
            state.report["simulation_progress"] = asdict(progress)
            state.report["residuals"] = progress.residuals
            state.report["converged"] = progress.converged

            if not all(r.success for r in step_results):
                state.report["status"] = "simulation_failed"
                failed = next(r for r in step_results if not r.success)
                msg = f"Command failed: {failed.command} (see {failed.log_file})"
                state.report.setdefault("issues", []).append(msg)
                return "failed", msg

            conv = "converged" if progress.converged else f"finished at iteration {progress.iteration}"
            summary = format_progress_summary(progress)
            if state.on_line:
                state.on_line(f"=== Simulation complete — {conv} ===")
            return "success", f"{summary} via {state.report.get('execution_mode', 'unknown')}"

        except Exception as exc:  # noqa: BLE001
            state.report["status"] = "simulation_failed"
            state.report.setdefault("issues", []).append(str(exc))
            return "error", str(exc)
