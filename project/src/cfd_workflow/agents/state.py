"""Shared workflow state passed between stage agents."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Optional

from pydantic import BaseModel, ConfigDict, Field

from crewai.flow.runtime import FlowState

from cfd_workflow.models import CompleteParams, ParsedParams


class AgentTraceEntry(BaseModel):
    """Debug record for a single agent execution."""

    agent: str
    role: str
    status: str
    message: str = ""
    duration_ms: float = 0.0


class WorkflowState(FlowState):
    """Pipeline state threaded through CrewAI Flow and stage agents."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    prompt: str
    output_root: Path
    dry_run: bool = False
    use_docker: bool = False
    on_line: Optional[Callable[[str], None]] = None

    run_id: str = ""
    run_dir: Optional[Path] = None
    case_dir: Optional[Path] = None
    report: dict[str, Any] = Field(default_factory=dict)

    parsed: Optional[ParsedParams] = None
    params: Optional[CompleteParams] = None

    agent_trace: list[AgentTraceEntry] = Field(default_factory=list)

    def halted(self) -> bool:
        """True when the pipeline should skip remaining agents."""
        status = self.report.get("status", "")
        terminal = {
            "failed",
            "blocked",
            "simulation_failed",
            "postprocess_failed",
            "dry_run_complete",
            "completed",
        }
        return status in terminal
