"""Stage agents — one agent per pipeline step."""

from cfd_workflow.agents.base import StageAgent
from cfd_workflow.agents.case import CaseAgent
from cfd_workflow.agents.parser import ParserAgent
from cfd_workflow.agents.physics import PhysicsAgent
from cfd_workflow.agents.report import ReportAgent
from cfd_workflow.agents.simulation import SimulationAgent
from cfd_workflow.agents.state import AgentTraceEntry, WorkflowState
from cfd_workflow.agents.visualization import VisualizationAgent

STAGE_AGENTS: list[StageAgent] = [
    ParserAgent(),
    PhysicsAgent(),
    CaseAgent(),
    SimulationAgent(),
    VisualizationAgent(),
    ReportAgent(),
]

__all__ = [
    "AgentTraceEntry",
    "CaseAgent",
    "ParserAgent",
    "PhysicsAgent",
    "ReportAgent",
    "STAGE_AGENTS",
    "SimulationAgent",
    "StageAgent",
    "VisualizationAgent",
    "WorkflowState",
]
