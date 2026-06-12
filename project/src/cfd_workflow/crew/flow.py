"""CrewAI Flow — deterministic orchestration of stage agents."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from crewai.flow.flow import Flow, listen, start

from cfd_workflow.agents import (
    CaseAgent,
    ParserAgent,
    PhysicsAgent,
    ReportAgent,
    SimulationAgent,
    VisualizationAgent,
    WorkflowState,
)


class CFDWorkflowFlow(Flow[WorkflowState]):
    """Sequential agent pipeline: parse → physics → case → simulate → visualize → report."""

    @start()
    def initialize(self) -> None:
        output_root = Path(self.state.output_root)
        run_id = datetime.now(timezone.utc).strftime("run_%Y%m%d_%H%M%S")
        run_dir = output_root / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        self.state.run_id = run_id
        self.state.run_dir = run_dir
        self.state.report = {
            "prompt": self.state.prompt,
            "run_id": run_id,
            "run_dir": str(run_dir),
            "started_at": datetime.now(timezone.utc).isoformat(),
            "status": "started",
            "issues": [],
        }

    @listen(initialize)
    def parser_agent_step(self) -> None:
        if self.state.halted():
            return
        ParserAgent().execute(self.state)

    @listen(parser_agent_step)
    def physics_agent_step(self) -> None:
        if self.state.halted():
            return
        PhysicsAgent().execute(self.state)

    @listen(physics_agent_step)
    def case_agent_step(self) -> None:
        if self.state.halted():
            return
        CaseAgent().execute(self.state)

    @listen(case_agent_step)
    def simulation_agent_step(self) -> None:
        if self.state.halted():
            return
        SimulationAgent().execute(self.state)

    @listen(simulation_agent_step)
    def visualization_agent_step(self) -> None:
        if self.state.halted():
            return
        VisualizationAgent().execute(self.state)

    @listen(visualization_agent_step)
    def report_agent_step(self) -> None:
        ReportAgent().execute(self.state)


def run_workflow_flow(
    prompt: str,
    output_root: Path,
    dry_run: bool = False,
    use_docker: bool = False,
    on_line=None,
) -> dict:
    """Execute the CFD workflow via CrewAI Flow and stage agents."""
    state = WorkflowState(
        prompt=prompt,
        output_root=Path(output_root),
        dry_run=dry_run,
        use_docker=use_docker,
        on_line=on_line,
    )
    flow = CFDWorkflowFlow(initial_state=state, suppress_flow_events=True)
    flow.kickoff()
    report = dict(flow.state.report)
    report["agent_trace"] = [entry.model_dump() for entry in flow.state.agent_trace]
    return report
