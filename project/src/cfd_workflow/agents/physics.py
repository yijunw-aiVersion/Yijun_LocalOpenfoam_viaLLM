"""Physics stage agent — parameter completion and validation."""

from __future__ import annotations

from cfd_workflow.agents.base import StageAgent
from cfd_workflow.agents.state import WorkflowState
from cfd_workflow.physics.parameters import complete_parameters, validate_parameters


class PhysicsAgent(StageAgent):
    name = "physics_agent"
    role = "CFD Parameter Engineer"

    def _run(self, state: WorkflowState) -> tuple[str, str]:
        if state.parsed is None:
            state.report["status"] = "failed"
            msg = "Parser agent did not produce parsed parameters"
            state.report.setdefault("issues", []).append(msg)
            return "failed", msg

        params = complete_parameters(state.parsed)
        state.params = params
        state.report["parameters"] = params.model_dump(mode="json")

        param_errors = validate_parameters(params)
        if param_errors:
            state.report["status"] = "failed"
            state.report.setdefault("issues", []).extend(param_errors)
            return "failed", "; ".join(param_errors)

        return (
            "success",
            f"D={params.diameter_m} m, Re={params.reynolds}, U={params.velocity_ms} m/s",
        )
