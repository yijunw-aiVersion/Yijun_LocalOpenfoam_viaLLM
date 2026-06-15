"""Tests for simulation log monitoring."""

from __future__ import annotations

from cfd_workflow.openfoam.monitor import (
    DEFAULT_RESIDUAL_TOL,
    SimulationProgress,
    format_progress_summary,
    is_converged,
    parse_residuals,
    update_progress_from_line,
)

SAMPLE_LOG = """
Time = 198

smoothSolver:  Solving for Ux, Initial residual = 0.00012, Final residual = 1.2e-05
smoothSolver:  Solving for Uy, Initial residual = 0.00008, Final residual = 8e-06
GAMG:  Solving for p, Initial residual = 0.00015, Final residual = 1.5e-05

Time = 199

smoothSolver:  Solving for Ux, Initial residual = 9.5e-05, Final residual = 9e-06
smoothSolver:  Solving for Uy, Initial residual = 7.1e-05, Final residual = 7e-06
GAMG:  Solving for p, Initial residual = 8.8e-05, Final residual = 8e-06
"""


def test_parse_residuals_from_log():
    residuals = parse_residuals(SAMPLE_LOG)
    assert residuals["U"] == 7.1e-05
    assert residuals["p"] == 8.8e-05


def test_is_converged():
    assert is_converged({"U": 1e-5, "p": 1e-5})
    assert not is_converged({"U": 1e-3, "p": 1e-5})
    assert not is_converged({})
    assert is_converged({"U": DEFAULT_RESIDUAL_TOL, "p": DEFAULT_RESIDUAL_TOL})


def test_update_progress_from_line():
    progress = SimulationProgress(max_iterations=200, step="simpleFoam", status="running")
    for line in SAMPLE_LOG.splitlines():
        update_progress_from_line(progress, line)

    assert progress.iteration == 199
    assert progress.residuals["p"] == 8.8e-05
    assert progress.converged is True


def test_format_progress_summary():
    progress = SimulationProgress(
        step="simpleFoam",
        status="running",
        iteration=50,
        max_iterations=200,
        residuals={"U": 0.001, "p": 0.0002},
    )
    text = format_progress_summary(progress)
    assert "iteration 50/200" in text
    assert "U=" in text
    assert "p=" in text
