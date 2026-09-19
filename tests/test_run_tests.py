"""Tests for run_tests."""

import sys
from types import SimpleNamespace
from unittest.mock import patch

from repopilot.tools.run_tests import run_tests
from repopilot.workspace import Workspace


def test_run_tests_successful_pytest_run(tmp_path):
    workspace = Workspace(tmp_path)
    completed = SimpleNamespace(returncode=0, stdout="1 passed", stderr="")

    with patch("repopilot.tools.run_tests.subprocess.run", return_value=completed) as mock_run:
        result = run_tests(workspace=workspace)

    assert result.success is True
    assert result.output == {
        "exit_code": 0,
        "stdout": "1 passed",
        "stderr": "",
    }
    assert result.error is None
    mock_run.assert_called_once_with(
        [sys.executable, "-m", "pytest"],
        cwd=workspace.root,
        capture_output=True,
        text=True,
        shell=False,
    )


def test_run_tests_failing_pytest_still_succeeds(tmp_path):
    workspace = Workspace(tmp_path)
    completed = SimpleNamespace(returncode=1, stdout="1 failed", stderr="")

    with patch("repopilot.tools.run_tests.subprocess.run", return_value=completed):
        result = run_tests(workspace=workspace)

    assert result.success is True
    assert result.output["exit_code"] == 1
    assert result.output["stdout"] == "1 failed"
    assert result.error is None


def test_run_tests_captures_stdout(tmp_path):
    workspace = Workspace(tmp_path)
    completed = SimpleNamespace(returncode=0, stdout="collected 2 items", stderr="")

    with patch("repopilot.tools.run_tests.subprocess.run", return_value=completed):
        result = run_tests(workspace=workspace)

    assert result.output["stdout"] == "collected 2 items"


def test_run_tests_captures_stderr(tmp_path):
    workspace = Workspace(tmp_path)
    completed = SimpleNamespace(returncode=0, stdout="", stderr="warning: slow test")

    with patch("repopilot.tools.run_tests.subprocess.run", return_value=completed):
        result = run_tests(workspace=workspace)

    assert result.output["stderr"] == "warning: slow test"


def test_run_tests_uses_workspace_root_as_cwd(tmp_path):
    workspace = Workspace(tmp_path)
    completed = SimpleNamespace(returncode=0, stdout="", stderr="")

    with patch("repopilot.tools.run_tests.subprocess.run", return_value=completed) as mock_run:
        run_tests(workspace=workspace)

    assert mock_run.call_args.kwargs["cwd"] == workspace.root


def test_run_tests_populates_duration_ms(tmp_path):
    workspace = Workspace(tmp_path)
    completed = SimpleNamespace(returncode=0, stdout="", stderr="")

    with patch("repopilot.tools.run_tests.subprocess.run", return_value=completed):
        result = run_tests(workspace=workspace)

    assert result.duration_ms is not None
    assert result.duration_ms >= 0


def test_run_tests_launch_failure_returns_error(tmp_path):
    workspace = Workspace(tmp_path)

    with patch(
        "repopilot.tools.run_tests.subprocess.run",
        side_effect=OSError("No such file or directory"),
    ):
        result = run_tests(workspace=workspace)

    assert result.success is False
    assert "Failed to run tests" in result.error
    assert result.duration_ms is not None
