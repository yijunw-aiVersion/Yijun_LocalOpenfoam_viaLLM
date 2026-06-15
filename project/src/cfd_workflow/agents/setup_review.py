"""Setup review stage — surface OpenFOAM case configuration to the user."""

from __future__ import annotations

from cfd_workflow.agents.base import StageAgent
from cfd_workflow.agents.state import WorkflowState
from cfd_workflow.openfoam.case_generator import build_case_config
from cfd_workflow.openfoam.monitor import format_case_setup_lines


class SetupReviewAgent(StageAgent):
    name = "setup_review_agent"
    role = "OpenFOAM Case Configuration Reviewer"

    def _run(self, state: WorkflowState) -> tuple[str, str]:
        if state.params is None or state.case_dir is None:
            state.report["status"] = "failed"
            msg = "Missing parameters or case directory for setup review"
            state.report.setdefault("issues", []).append(msg)
            return "failed", msg

        config = build_case_config(state.params, max_iterations=state.max_iterations)
        state.report["case_setup"] = config

        if state.on_line:
            for line in format_case_setup_lines(config):
                state.on_line(line)

        if state.dry_run:
            state.report["status"] = "dry_run_complete"
            return "success", "Case configuration reviewed (dry run — solver skipped)"

        solver = config["solver"]
        return (
            "success",
            f"Case ready: {solver['name']}, {solver['max_iterations']} iterations, "
            f"Re={config['fluid']['reynolds']}",
        )
