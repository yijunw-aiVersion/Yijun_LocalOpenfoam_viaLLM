"""Report stage agent — JSON/Markdown run reports."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from cfd_workflow.agents.base import StageAgent
from cfd_workflow.agents.state import WorkflowState


class ReportAgent(StageAgent):
    name = "report_agent"
    role = "Workflow Report Writer"

    def _run(self, state: WorkflowState) -> tuple[str, str]:
        if state.run_dir is None:
            return "skipped", "No run directory to write report"

        self._write_reports(state)
        return "success", f"Report written to {state.run_dir}"

    def execute(self, state: WorkflowState) -> WorkflowState:
        state = super().execute(state)
        if state.run_dir is not None:
            self._write_reports(state)
        return state

    def _write_reports(self, state: WorkflowState) -> None:
        run_dir = state.run_dir
        assert run_dir is not None
        report = state.report
        report["agent_trace"] = [entry.model_dump() for entry in state.agent_trace]
        report.setdefault("finished_at", datetime.now(timezone.utc).isoformat())

        (run_dir / "run_report.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        md_lines = [
            f"# Run report — {report.get('run_id', 'unknown')}",
            "",
            f"- **Status:** {report.get('status')}",
            f"- **Prompt:** {report.get('prompt')}",
            "",
        ]
        if report.get("parameters"):
            p = report["parameters"]
            md_lines.append(
                f"- **Parameters:** D={p['diameter_m']} m, Re={p['reynolds']}, "
                f"U={p['velocity_ms']} m/s, fluid={p['fluid']}"
            )
        if report.get("execution_mode"):
            md_lines.append(f"- **Execution:** {report['execution_mode']}")
        if report.get("solver"):
            s = report["solver"]
            md_lines.append(
                f"- **Solver:** max_iterations={s['max_iterations']}, "
                f"write_interval={s['write_interval']}"
            )
        if report.get("issues"):
            md_lines.extend(["", "## Issues", ""])
            md_lines.extend(f"- {issue}" for issue in report["issues"])
        if report.get("figures"):
            md_lines.extend(["", "## Figures", ""])
            for name, path in report["figures"].items():
                md_lines.append(f"- {name}: `{path}`")
        if report.get("agent_trace"):
            md_lines.extend(["", "## Agent trace", ""])
            for entry in report["agent_trace"]:
                md_lines.append(
                    f"- **{entry['agent']}** ({entry['role']}): "
                    f"{entry['status']} — {entry['message']} ({entry['duration_ms']} ms)"
                )

        (run_dir / "run_report.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")
