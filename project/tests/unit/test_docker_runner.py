"""Tests for Docker runner helpers."""

from unittest.mock import patch

from cfd_workflow.openfoam.docker_runner import ensure_image


def test_ensure_image_skips_pull_when_local():
    lines: list[str] = []

    with patch(
        "cfd_workflow.openfoam.docker_runner._image_exists_locally",
        return_value=True,
    ), patch("cfd_workflow.openfoam.docker_runner.subprocess.run") as run:
        ensure_image(on_line=lines.append)

    run.assert_not_called()
    assert lines == ["Using local Docker image: opencfd/openfoam-default:2412"]


def test_ensure_image_pulls_when_missing():
    lines: list[str] = []

    with patch(
        "cfd_workflow.openfoam.docker_runner._image_exists_locally",
        return_value=False,
    ), patch(
        "cfd_workflow.openfoam.docker_runner.subprocess.run",
        return_value=type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})(),
    ) as run:
        ensure_image(on_line=lines.append)

    run.assert_called_once()
    assert run.call_args.args[0] == ["docker", "pull", "opencfd/openfoam-default:2412"]
    assert lines[0].startswith("Pulling Docker image:")
