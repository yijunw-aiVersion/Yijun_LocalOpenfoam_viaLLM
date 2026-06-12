"""Parser stage agent — natural language input."""

from __future__ import annotations

from cfd_workflow.agents.base import StageAgent
from cfd_workflow.agents.state import WorkflowState
from cfd_workflow.parser.nl_parser import parse_nl_input
from cfd_workflow.physics.parameters import missing_fields_prompt


class ParserAgent(StageAgent):
    name = "parser_agent"
    role = "Natural Language Parser"

    def _run(self, state: WorkflowState) -> tuple[str, str]:
        parsed = parse_nl_input(state.prompt)
        state.parsed = parsed
        follow_up = missing_fields_prompt(parsed)
        if follow_up:
            state.report["status"] = "failed"
            state.report.setdefault("issues", []).append(follow_up)
            return "failed", follow_up
        return "success", "Parsed natural language input"
