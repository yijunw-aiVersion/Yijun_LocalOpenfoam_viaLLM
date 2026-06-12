"""Case generation stage agent — OpenFOAM case files."""

from __future__ import annotations

from cfd_workflow.agents.base import StageAgent
from cfd_workflow.agents.state import WorkflowState
from cfd_workflow.openfoam.case_generator import render_case, validate_case


class CaseAgent(StageAgent):
    name = "case_agent"
    role = "OpenFOAM Case Generator"

    def _run(self, state: WorkflowState) -> tuple[str, str]:
        if state.params is None or state.run_dir is None:
            state.report["status"] = "failed"
            msg = "Missing parameters or run directory for case generation"
            state.report.setdefault("issues", []).append(msg)
            return "failed", msg

        case_dir = state.run_dir / "case"
        render_case(state.params, case_dir)
        missing = validate_case(case_dir)
        state.case_dir = case_dir
        state.report["case_dir"] = str(case_dir)

        if missing:
            state.report["status"] = "failed"
            msg = f"Missing case files: {missing}"
            state.report.setdefault("issues", []).append(msg)
            return "failed", msg

        state.report["status"] = "case_generated"
        if state.dry_run:
            state.report["status"] = "dry_run_complete"
            return "success", "Case generated (dry run — solver skipped)"

        return "success", f"OpenFOAM case written to {case_dir}"
