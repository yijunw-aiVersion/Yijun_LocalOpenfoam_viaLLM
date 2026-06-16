from pathlib import Path
from typing import Optional

import typer

from cfd_workflow.openfoam.case_generator import DEFAULT_MAX_ITERATIONS
from cfd_workflow.openfoam.monitor import DEFAULT_RESIDUAL_TOL


def _parse_dimension_option(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = value.lower()
    if normalized not in {"2d", "3d"}:
        raise typer.BadParameter("dimension must be '2d' or '3d'")
    return normalized


def main(
    prompt: str = typer.Argument(..., help="Natural language simulation description"),
    output_dir: Path = typer.Option(
        Path("../test"),
        help="Directory to store run outputs",
    ),
    dry_run: bool = typer.Option(False, help="Only parse and generate case, do not solve"),
    docker: bool = typer.Option(False, help="Run OpenFOAM inside Docker (opencfd/openfoam-default)"),
    max_iterations: int = typer.Option(
        DEFAULT_MAX_ITERATIONS,
        "--max-iterations",
        min=1,
        help="simpleFoam outer iterations (controlDict endTime; default 200)",
    ),
    residual_tol: float = typer.Option(
        DEFAULT_RESIDUAL_TOL,
        "--residual-tol",
        min=1e-12,
        max=1.0,
        help="Early-stop when U and p initial residuals fall below this (default 1e-5)",
    ),
    dimension: Optional[str] = typer.Option(
        None,
        "--dimension",
        callback=_parse_dimension_option,
        help="Override simulation dimension: 2d or 3d (default: infer from prompt, else 2d)",
    ),
    span: float | None = typer.Option(
        None,
        "--span",
        min=0.0,
        help="3D cylinder span along z in meters (default: 10× diameter)",
    ),
    coarse_mesh: bool = typer.Option(
        False,
        "--coarse-mesh",
        help="Force coarse background mesh (3D uses coarse mesh by default)",
    ),
    fine_mesh: bool = typer.Option(
        False,
        "--fine-mesh",
        help="Disable auto-coarse mesh for 3D runs",
    ),
) -> None:
    """Run a full CFD workflow from natural language input."""
    from cfd_workflow.workflow import run_workflow

    def echo_line(line: str) -> None:
        typer.echo(line)

    report = run_workflow(
        prompt,
        output_root=output_dir.resolve(),
        dry_run=dry_run,
        use_docker=docker,
        max_iterations=max_iterations,
        residual_tol=residual_tol,
        dimension=dimension,
        span=span,
        coarse_mesh=coarse_mesh,
        fine_mesh=fine_mesh,
        on_line=echo_line,
    )
    typer.echo(f"Status: {report['status']}")
    typer.echo(f"Run directory: {report['run_dir']}")
    if report.get("parameters", {}).get("dimension"):
        typer.echo(f"Dimension: {report['parameters']['dimension']}")
    if report.get("parameters", {}).get("span_m"):
        typer.echo(f"Span: {report['parameters']['span_m']} m")
    if report.get("residual_tol") is not None:
        typer.echo(f"Residual tolerance: {report['residual_tol']:.2e}")
    if report.get("converged") is not None:
        typer.echo(f"Converged: {report['converged']}")
    if report.get("stopped_early"):
        typer.echo("Stopped early: yes (steady-state tolerance reached)")
    if report.get("residuals"):
        res = ", ".join(f"{k}={v:.2e}" for k, v in report["residuals"].items())
        typer.echo(f"Final residuals: {res}")
    if report.get("execution_mode"):
        typer.echo(f"Execution: {report['execution_mode']}")
    if report.get("issues"):
        for issue in report["issues"]:
            typer.echo(f"Issue: {issue}")
    if report.get("figures"):
        for name, path in report["figures"].items():
            typer.echo(f"Figure {name}: {path}")
    if report["status"] not in {"completed", "dry_run_complete", "case_generated"}:
        raise typer.Exit(code=1)


def entrypoint() -> None:
    typer.run(main)


if __name__ == "__main__":
    entrypoint()
