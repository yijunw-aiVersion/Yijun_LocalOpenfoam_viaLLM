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
    on_line=None,
) -> dict:
    """Run NL → case → solver → plots pipeline via CrewAI Flow."""
    from cfd_workflow.openfoam.case_generator import DEFAULT_MAX_ITERATIONS
    from cfd_workflow.openfoam.monitor import DEFAULT_RESIDUAL_TOL

    return run_workflow_flow(
        prompt,
        output_root,
        dry_run=dry_run,
        use_docker=use_docker,
        max_iterations=max_iterations or DEFAULT_MAX_ITERATIONS,
        residual_tol=residual_tol if residual_tol is not None else DEFAULT_RESIDUAL_TOL,
        on_line=on_line,
    )
