"""Visualization stage agent — velocity and surface pressure plots."""

from __future__ import annotations

from cfd_workflow.agents.base import StageAgent
from cfd_workflow.agents.state import WorkflowState
from cfd_workflow.postprocess.visualize import generate_report


class VisualizationAgent(StageAgent):
    name = "visualization_agent"
    role = "CFD Post-Processing Analyst"

    def _run(self, state: WorkflowState) -> tuple[str, str]:
        if state.case_dir is None or state.run_dir is None or state.params is None:
            state.report["status"] = "postprocess_failed"
            msg = "Missing case, run directory, or parameters for visualization"
            state.report.setdefault("issues", []).append(msg)
            return "failed", msg

        figures_dir = state.run_dir / "figures"
        try:
            outputs = generate_report(
                state.case_dir,
                figures_dir,
                u_inf=state.params.velocity_ms,
                rho=state.params.density_kgm3,
                dimension=state.params.dimension,
            )
            state.report["figures"] = {k: str(v) for k, v in outputs.items()}
            if state.params.dimension.value == "3d":
                state.report["figure_notes"] = {
                    "velocity_field": "Mid-plane slice at z=0 (compare with 2D cross-section)",
                    "surface_pressure": "Cp on cylinder points near z=0 (mid-span)",
                }
            state.report["status"] = "completed"
            return "success", f"Figures written to {figures_dir}"
        except Exception as exc:  # noqa: BLE001
            state.report["status"] = "postprocess_failed"
            state.report.setdefault("issues", []).append(f"Visualization failed: {exc}")
            return "error", str(exc)
