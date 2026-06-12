"""End-to-end workflow orchestration (CrewAI Flow + stage agents)."""

from __future__ import annotations

from pathlib import Path

from cfd_workflow.crew.flow import run_workflow_flow


def run_workflow(
    prompt: str,
    output_root: Path,
    dry_run: bool = False,
    use_docker: bool = False,
    on_line=None,
) -> dict:
    """Run NL → case → solver → plots pipeline via CrewAI Flow."""
    return run_workflow_flow(
        prompt,
        output_root,
        dry_run=dry_run,
        use_docker=use_docker,
        on_line=on_line,
    )
