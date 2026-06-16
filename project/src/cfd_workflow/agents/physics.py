"""Physics stage agent — parameter completion and validation."""

from __future__ import annotations

from cfd_workflow.agents.base import StageAgent
from cfd_workflow.agents.state import WorkflowState
from cfd_workflow.models import SimulationDimension
from cfd_workflow.physics.parameters import (
    complete_parameters,
    parameter_warnings,
    validate_parameters,
)


class PhysicsAgent(StageAgent):
    name = "physics_agent"
    role = "CFD Parameter Engineer"

    def _run(self, state: WorkflowState) -> tuple[str, str]:
        if state.parsed is None:
            state.report["status"] = "failed"
            msg = "Parser agent did not produce parsed parameters"
            state.report.setdefault("issues", []).append(msg)
            return "failed", msg

        params = complete_parameters(
            state.parsed,
            dimension_override=state.dimension_override,
            span_override=state.span_override,
        )
        state.params = params
        state.report["parameters"] = params.model_dump(mode="json")

        param_errors = validate_parameters(params)
        if param_errors:
            state.report["status"] = "failed"
            state.report.setdefault("issues", []).extend(param_errors)
            return "failed", "; ".join(param_errors)

        for warning in parameter_warnings(params):
            state.report.setdefault("warnings", []).append(warning)
            if state.on_line:
                state.on_line(f"Warning: {warning}")

        dim = params.dimension.value.upper()
        span_note = ""
        if params.dimension == SimulationDimension.THREE_D and params.span_m is not None:
            span_note = f", L={params.span_m:.4g} m (L/D={params.span_ratio:.1f})"

        return (
            "success",
            f"{dim}: D={params.diameter_m} m, Re={params.reynolds}, U={params.velocity_ms} m/s{span_note}",
        )
