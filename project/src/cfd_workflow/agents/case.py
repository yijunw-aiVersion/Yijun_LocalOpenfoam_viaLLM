"""Case generation stage agent — OpenFOAM case files."""

from __future__ import annotations

from cfd_workflow.agents.base import StageAgent
from cfd_workflow.agents.state import WorkflowState
from cfd_workflow.openfoam.case_generator import render_case, resolve_coarse_mesh, solver_settings, validate_case


class CaseAgent(StageAgent):
    name = "case_agent"
    role = "OpenFOAM Case Generator"

    def _run(self, state: WorkflowState) -> tuple[str, str]:
        if state.params is None or state.run_dir is None:
            state.report["status"] = "failed"
            msg = "Missing parameters or run directory for case generation"
            state.report.setdefault("issues", []).append(msg)
            return "failed", msg

        coarse = resolve_coarse_mesh(
            state.params,
            coarse_mesh=state.coarse_mesh,
            fine_mesh=state.fine_mesh,
        )
        state.report["coarse_mesh"] = coarse

        case_dir = state.run_dir / "case"
        render_case(
            state.params,
            case_dir,
            max_iterations=state.max_iterations,
            coarse=coarse,
        )
        missing = validate_case(case_dir)
        state.case_dir = case_dir
        state.report["case_dir"] = str(case_dir)
        state.report["solver"] = solver_settings(state.max_iterations)

        if missing:
            state.report["status"] = "failed"
            msg = f"Missing case files: {missing}"
            state.report.setdefault("issues", []).append(msg)
            return "failed", msg

        state.report["status"] = "case_generated"
        mesh_note = " (coarse mesh)" if coarse else ""
        return "success", (
            f"OpenFOAM case written to {case_dir}{mesh_note} "
            f"(max_iterations={state.max_iterations})"
        )
