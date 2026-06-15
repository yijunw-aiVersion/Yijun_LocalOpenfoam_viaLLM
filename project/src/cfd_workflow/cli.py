import typer
from pathlib import Path

from cfd_workflow.openfoam.case_generator import DEFAULT_MAX_ITERATIONS

app = typer.Typer(help="Natural language driven CFD workflow builder")


@app.command()
def run(
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
):
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
        on_line=echo_line,
    )
    typer.echo(f"Status: {report['status']}")
    typer.echo(f"Run directory: {report['run_dir']}")
    if report.get("converged") is not None:
        typer.echo(f"Converged: {report['converged']}")
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


if __name__ == "__main__":
    app()
