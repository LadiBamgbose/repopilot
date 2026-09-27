"""Run the repository pytest suite."""

import subprocess
import sys
import time

from pydantic import BaseModel, ConfigDict

from repopilot.core.tool_protocol import ToolResult
from repopilot.workspace import Workspace


class RunTestsArgs(BaseModel):
    """Arguments for ``run_tests``. This tool takes no caller arguments."""

    model_config = ConfigDict(extra="forbid")


def run_tests(*, workspace: Workspace) -> ToolResult:
    """Run pytest for the workspace using the current Python interpreter.

    The tool succeeds when the pytest process launches and completes. Test
    failures are reported via a non-zero ``exit_code`` in the output payload,
    not via ``ToolResult.success``. Launch failures return ``success=False``.
    """
    command = [sys.executable, "-m", "pytest"]
    started = time.perf_counter()

    try:
        completed = subprocess.run(
            command,
            cwd=workspace.root,
            capture_output=True,
            text=True,
            shell=False,
        )
    except OSError as exc:
        duration_ms = int((time.perf_counter() - started) * 1000)
        return ToolResult(
            success=False,
            error=f"Failed to run tests: {exc}",
            duration_ms=duration_ms,
        )

    duration_ms = int((time.perf_counter() - started) * 1000)
    return ToolResult(
        success=True,
        output={
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        },
        duration_ms=duration_ms,
    )
