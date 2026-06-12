"""CrewAI agent definitions (YAML-backed roles and tool assignments)."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

import yaml
from crewai import Agent

from cfd_workflow.crew.tools import TOOLS_BY_NAME


_CONFIG_DIR = Path(__file__).parent / "config"


def load_agents_config() -> dict:
    with (_CONFIG_DIR / "agents.yaml").open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_tasks_config() -> dict:
    with (_CONFIG_DIR / "tasks.yaml").open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


# Tool assignment per agent — maps agent key → tool names from crew/tools.py
AGENT_TOOLS: ClassVar[dict[str, list[str]]] = {
    "parser_agent": ["parse_nl_prompt"],
    "physics_agent": ["complete_physics_parameters"],
    "case_agent": ["render_openfoam_case"],
    "simulation_agent": ["run_openfoam_local", "run_openfoam_docker"],
    "visualization_agent": ["generate_cfd_figures"],
    "report_agent": [],
}


def build_crewai_agents(*, verbose: bool = False) -> dict[str, Agent]:
    """Build CrewAI Agent objects from YAML config (for inspection / future LLM mode)."""
    configs = load_agents_config()
    agents: dict[str, Agent] = {}
    for key, cfg in configs.items():
        tool_names = AGENT_TOOLS.get(key, [])
        tools = [TOOLS_BY_NAME[name] for name in tool_names if name in TOOLS_BY_NAME]
        agents[key] = Agent(
            role=cfg["role"].strip(),
            goal=cfg["goal"].strip(),
            backstory=cfg["backstory"].strip(),
            tools=tools,
            verbose=verbose,
            allow_delegation=False,
        )
    return agents
