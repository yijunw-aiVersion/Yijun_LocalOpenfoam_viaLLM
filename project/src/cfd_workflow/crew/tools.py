"""CrewAI tools — thin wrappers around existing pipeline functions."""

from __future__ import annotations

import json
from pathlib import Path

from crewai.tools import tool

from cfd_workflow.models import CompleteParams
from cfd_workflow.openfoam.case_generator import render_case, validate_case
from cfd_workflow.openfoam.docker_runner import run_simulation_docker
from cfd_workflow.openfoam.runner import run_simulation
from cfd_workflow.parser.nl_parser import parse_nl_input
from cfd_workflow.physics.parameters import complete_parameters, missing_fields_prompt, validate_parameters
from cfd_workflow.postprocess.visualize import generate_report


@tool("parse_nl_prompt")
def parse_nl_prompt_tool(prompt: str) -> str:
    """Parse natural language CFD prompt into structured parameters."""
    parsed = parse_nl_input(prompt)
    follow_up = missing_fields_prompt(parsed)
    payload = {"parsed": parsed.model_dump(mode="json"), "follow_up": follow_up}
    return json.dumps(payload, ensure_ascii=False)


@tool("complete_physics_parameters")
def complete_physics_parameters_tool(parsed_json: str) -> str:
    """Complete and validate physics parameters from parsed JSON."""
    from cfd_workflow.models import ParsedParams

    parsed = ParsedParams.model_validate_json(parsed_json)
    params = complete_parameters(parsed)
    errors = validate_parameters(params)
    payload = {"params": params.model_dump(mode="json"), "errors": errors}
    return json.dumps(payload, ensure_ascii=False)


@tool("render_openfoam_case")
def render_openfoam_case_tool(params_json: str, case_dir: str) -> str:
    """Render OpenFOAM case files into the given directory."""
    params = CompleteParams.model_validate_json(params_json)
    target = Path(case_dir)
    render_case(params, target)
    missing = validate_case(target)
    return json.dumps({"case_dir": str(target), "missing": missing}, ensure_ascii=False)


@tool("run_openfoam_local")
def run_openfoam_local_tool(case_dir: str) -> str:
    """Run OpenFOAM solver pipeline locally."""
    results, progress = run_simulation(Path(case_dir))
    payload = {
        "steps": [
            {"command": r.command, "success": r.success, "log": str(r.log_file)} for r in results
        ],
        "progress": {
            "iteration": progress.iteration,
            "converged": progress.converged,
            "residuals": progress.residuals,
        },
    }
    return json.dumps(payload, ensure_ascii=False)


@tool("run_openfoam_docker")
def run_openfoam_docker_tool(case_dir: str) -> str:
    """Run OpenFOAM solver pipeline inside Docker."""
    results, progress = run_simulation_docker(Path(case_dir))
    payload = {
        "steps": [
            {"command": r.command, "success": r.success, "log": str(r.log_file)} for r in results
        ],
        "progress": {
            "iteration": progress.iteration,
            "converged": progress.converged,
            "residuals": progress.residuals,
        },
    }
    return json.dumps(payload, ensure_ascii=False)


@tool("generate_cfd_figures")
def generate_cfd_figures_tool(case_dir: str, figures_dir: str, u_inf: float, rho: float) -> str:
    """Generate velocity and surface pressure PNG figures."""
    outputs = generate_report(Path(case_dir), Path(figures_dir), u_inf=u_inf, rho=rho)
    return json.dumps({k: str(v) for k, v in outputs.items()}, ensure_ascii=False)


ALL_TOOLS = [
    parse_nl_prompt_tool,
    complete_physics_parameters_tool,
    render_openfoam_case_tool,
    run_openfoam_local_tool,
    run_openfoam_docker_tool,
    generate_cfd_figures_tool,
]

TOOLS_BY_NAME = {t.name: t for t in ALL_TOOLS}
