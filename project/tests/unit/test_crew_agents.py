"""Tests for CrewAI agent structure and Flow orchestration."""

from __future__ import annotations

from pathlib import Path

import pytest

from cfd_workflow.agents import STAGE_AGENTS
from cfd_workflow.crew.definitions import AGENT_TOOLS, build_crewai_agents, load_agents_config
from cfd_workflow.workflow import run_workflow


def test_stage_agents_registered():
    names = [agent.name for agent in STAGE_AGENTS]
    assert names == [
        "parser_agent",
        "physics_agent",
        "case_agent",
        "simulation_agent",
        "visualization_agent",
        "report_agent",
    ]


def test_agents_yaml_matches_stage_agents():
    config = load_agents_config()
    assert set(config) == {agent.name for agent in STAGE_AGENTS}


def test_agent_tools_cover_pipeline():
    assert set(AGENT_TOOLS) == {agent.name for agent in STAGE_AGENTS}


def test_build_crewai_agents():
    agents = build_crewai_agents(verbose=False)
    assert set(agents) == {agent.name for agent in STAGE_AGENTS}
    assert agents["parser_agent"].role.strip()


@pytest.mark.parametrize(
    "prompt,expected_status",
    [
        ("圆柱直径0.1米，雷诺数100，来流速度1米每秒。", "dry_run_complete"),
    ],
)
def test_workflow_dry_run_via_flow(tmp_path: Path, prompt: str, expected_status: str):
    report = run_workflow(prompt, tmp_path, dry_run=True)
    assert report["status"] == expected_status
    assert (tmp_path / report["run_id"] / "case" / "system" / "blockMeshDict").exists()
    trace_agents = [entry["agent"] for entry in report["agent_trace"]]
    assert trace_agents[:3] == ["parser_agent", "physics_agent", "case_agent"]
    assert trace_agents[-1] == "report_agent"
