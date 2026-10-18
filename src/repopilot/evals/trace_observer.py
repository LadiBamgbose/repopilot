"""Collect bounded step-level traces from agent events."""

import re
from typing import Any

from pydantic import BaseModel, ConfigDict

from repopilot.agent.observer import (
    AgentEvent,
    FinalAnswerReached,
    ModelResponseReceived,
    ToolCallRequested,
    ToolResultReturned,
)

_MAX_SUMMARY_CHARS = 240
_FAILED_LINE = re.compile(r"^FAILED\s+\S+")
_SHORT_SUMMARY = re.compile(r"^=+ short test summary info =+$")


class TraceEvent(BaseModel):
    """One structured step from a benchmark agent run."""

    model_config = ConfigDict(extra="forbid")

    step: int
    event_type: str
    response_type: str | None = None
    tool_name: str | None = None
    tool_arguments: dict[str, Any] | None = None
    tool_success: bool | None = None
    result_summary: str | None = None
    path: str | None = None
    exit_code: int | None = None
    failure_summary: str | None = None
    final_answer: str | None = None


class BenchmarkTraceObserver:
    """Record a readable execution trace for one benchmark task."""

    def __init__(self, *, max_summary_chars: int = _MAX_SUMMARY_CHARS) -> None:
        self._max_summary_chars = max_summary_chars
        self.events: list[TraceEvent] = []

    def on_event(self, event: AgentEvent) -> None:
        if isinstance(event, ModelResponseReceived):
            self.events.append(
                TraceEvent(
                    step=event.step,
                    event_type="model_response",
                    response_type=event.response.type,
                )
            )
            return
        if isinstance(event, ToolCallRequested):
            arguments = dict(event.tool_call.arguments)
            self.events.append(
                TraceEvent(
                    step=event.step,
                    event_type="tool_call",
                    tool_name=event.tool_call.tool_name,
                    tool_arguments=_bounded_arguments(arguments),
                    path=_file_path(arguments),
                )
            )
            return
        if isinstance(event, ToolResultReturned):
            arguments = dict(event.tool_call.arguments)
            exit_code, failure_summary = _run_tests_details(event.result)
            self.events.append(
                TraceEvent(
                    step=event.step,
                    event_type="tool_result",
                    tool_name=event.tool_call.tool_name,
                    tool_arguments=_bounded_arguments(arguments),
                    tool_success=event.result.success,
                    result_summary=_result_summary(
                        event.result,
                        max_chars=self._max_summary_chars,
                    ),
                    path=_file_path(arguments),
                    exit_code=exit_code,
                    failure_summary=failure_summary,
                )
            )
            return
        if isinstance(event, FinalAnswerReached):
            self.events.append(
                TraceEvent(
                    step=event.step,
                    event_type="final_answer",
                    final_answer=_truncate(
                        event.final_answer,
                        self._max_summary_chars,
                    ),
                )
            )


def format_trace(events: list[TraceEvent]) -> str:
    """Render a compact multi-line trace for CLI output."""
    lines: list[str] = []
    for event in events:
        if event.event_type == "model_response":
            lines.append(
                f"step {event.step}: model_response type={event.response_type}"
            )
        elif event.event_type == "tool_call":
            detail = f"args={event.tool_arguments}"
            if event.path is not None:
                detail = f"path={event.path} {detail}"
            lines.append(
                f"step {event.step}: tool_call {event.tool_name} {detail}"
            )
        elif event.event_type == "tool_result":
            parts = [f"success={event.tool_success}"]
            if event.path is not None:
                parts.append(f"path={event.path}")
            if event.exit_code is not None:
                parts.append(f"exit_code={event.exit_code}")
            if event.failure_summary:
                parts.append(f"failures={event.failure_summary}")
            elif event.result_summary:
                parts.append(f"summary={event.result_summary}")
            lines.append(
                f"step {event.step}: tool_result {event.tool_name} "
                + " ".join(parts)
            )
        else:
            lines.append(
                f"step {event.step}: final_answer {event.final_answer}"
            )
    return "\n".join(lines)


def _file_path(arguments: dict[str, Any]) -> str | None:
    path = arguments.get("path")
    return path if isinstance(path, str) else None


def _bounded_arguments(arguments: dict[str, Any]) -> dict[str, Any]:
    bounded: dict[str, Any] = {}
    for key, value in arguments.items():
        if key == "contents" and isinstance(value, str):
            bounded[key] = _truncate(value, 80)
        else:
            bounded[key] = value
    return bounded


def _result_summary(result: Any, *, max_chars: int) -> str:
    if not result.success:
        return _truncate(result.error or "tool failed", max_chars)
    output = result.output
    if isinstance(output, dict) and "exit_code" in output:
        exit_code = output.get("exit_code")
        failure = _failure_summary_from_pytest_output(output.get("stdout") or "")
        if failure:
            return _truncate(f"exit_code={exit_code}; {failure}", max_chars)
        return _truncate(f"exit_code={exit_code}", max_chars)
    return _truncate(repr(output), max_chars)


def _run_tests_details(result: Any) -> tuple[int | None, str | None]:
    if not isinstance(result.output, dict) or "exit_code" not in result.output:
        return None, None
    exit_code = result.output.get("exit_code")
    if not isinstance(exit_code, int):
        return None, None
    failure_summary = None
    if exit_code != 0:
        failure_summary = _failure_summary_from_pytest_output(
            result.output.get("stdout") or ""
        )
    return exit_code, failure_summary


def _failure_summary_from_pytest_output(stdout: str) -> str | None:
    failed: list[str] = []
    in_short_summary = False
    for line in stdout.splitlines():
        if _SHORT_SUMMARY.match(line):
            in_short_summary = True
            continue
        if in_short_summary and _FAILED_LINE.match(line):
            failed.append(line.strip())
        elif line.startswith("FAILED "):
            failed.append(line.strip())
    if not failed:
        return None
    return _truncate("; ".join(failed[:5]), _MAX_SUMMARY_CHARS)


def _truncate(value: str, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value
    return value[:max_chars] + "..."
