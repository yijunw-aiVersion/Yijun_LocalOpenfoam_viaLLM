"""End-to-end workflow orchestration (CrewAI Flow + stage agents)."""

from __future__ import annotations

from pathlib import Path

from cfd_workflow.crew.flow import run_workflow_flow


def run_workflow(
    prompt: str,
    output_root: Path,
    dry_run: bool = False,
    use_docker: bool = False,
    max_iterations: int | None = None,
    residual_tol: float | None = None,
    dimension: str | None = None,
    span: float | None = None,
    coarse_mesh: bool = False,
    fine_mesh: bool = False,
    on_line=None,
) -> dict:
    """Run NL → case → solver → plots pipeline via CrewAI Flow."""
    from cfd_workflow.models import SimulationDimension
    from cfd_workflow.openfoam.case_generator import DEFAULT_MAX_ITERATIONS
    from cfd_workflow.openfoam.monitor import DEFAULT_RESIDUAL_TOL

    dimension_override = None
    if dimension is not None:
        dimension_override = SimulationDimension(dimension.lower())

    return run_workflow_flow(
        prompt,
        output_root,
        dry_run=dry_run,
        use_docker=use_docker,
        max_iterations=max_iterations or DEFAULT_MAX_ITERATIONS,
        residual_tol=residual_tol if residual_tol is not None else DEFAULT_RESIDUAL_TOL,
        dimension_override=dimension_override,
        span_override=span,
        coarse_mesh=coarse_mesh,
        fine_mesh=fine_mesh,
        on_line=on_line,
    )
