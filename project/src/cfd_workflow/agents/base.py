"""Base class for deterministic stage agents."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod

from cfd_workflow.agents.state import AgentTraceEntry, WorkflowState


class StageAgent(ABC):
    """One pipeline stage, owned by a named agent for easier debugging."""

    name: str
    role: str

    @abstractmethod
    def _run(self, state: WorkflowState) -> tuple[str, str]:
        """Execute stage logic. Returns (status, message)."""

    def execute(self, state: WorkflowState) -> WorkflowState:
        started = time.monotonic()
        status, message = "success", ""
        try:
            status, message = self._run(state)
        except Exception as exc:  # noqa: BLE001
            status = "error"
            message = str(exc)
            state.report.setdefault("issues", []).append(message)
            if state.report.get("status") == "started":
                state.report["status"] = "failed"
        finally:
            elapsed_ms = (time.monotonic() - started) * 1000.0
            state.agent_trace.append(
                AgentTraceEntry(
                    agent=self.name,
                    role=self.role,
                    status=status,
                    message=message,
                    duration_ms=round(elapsed_ms, 2),
                )
            )
        return state
