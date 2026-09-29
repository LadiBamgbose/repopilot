"""Optional callbacks for agent-loop steps."""

import json
import re
import sys
from dataclasses import dataclass
from typing import Any, Protocol, TextIO

from repopilot.agent.schemas import AgentResponse
from repopilot.core.tool_protocol import ToolCall, ToolResult

_SECRET_MARKERS = (
    "api_key",
    "apikey",
    "token",
    "secret",
    "password",
    "authorization",
)
_API_KEY_TEXT = re.compile(r"sk-[A-Za-z0-9_\-]{8,}")
_DEFAULT_MAX_CHARS = 200


@dataclass(frozen=True)
class ModelResponseReceived:
    """The model returned a tool call or a final answer."""

    step: int
    response: AgentResponse


@dataclass(frozen=True)
class ToolCallRequested:
    """The runner is about to execute one tool call."""

    step: int
    tool_call: ToolCall


@dataclass(frozen=True)
class ToolResultReturned:
    """A tool finished and produced a ToolResult."""

    step: int
    tool_call: ToolCall
    result: ToolResult


@dataclass(frozen=True)
class FinalAnswerReached:
    """The model ended the run with a final answer."""

    step: int
    final_answer: str


AgentEvent = (
    ModelResponseReceived
    | ToolCallRequested
    | ToolResultReturned
    | FinalAnswerReached
)


class AgentObserver(Protocol):
    """Receives agent events in the order the runner produces them."""

    def on_event(self, event: AgentEvent) -> None:
        """Handle one agent-loop event."""
        ...


class ConsoleAgentObserver:
    """Print a short, redacted trace of each agent event."""

    def __init__(
        self,
        *,
        file: TextIO | None = None,
        max_chars: int = _DEFAULT_MAX_CHARS,
    ) -> None:
        self._file = sys.stdout if file is None else file
        self._max_chars = max_chars

    def on_event(self, event: AgentEvent) -> None:
        print(_format_event(event, max_chars=self._max_chars), file=self._file)


def _format_event(event: AgentEvent, *, max_chars: int) -> str:
    if isinstance(event, ModelResponseReceived):
        return f"step {event.step}: model response {event.response.type}"
    if isinstance(event, ToolCallRequested):
        arguments = _preview(event.tool_call.arguments, max_chars)
        return (
            f"step {event.step}: tool call {event.tool_call.tool_name} "
            f"arguments={arguments}"
        )
    if isinstance(event, ToolResultReturned):
        if event.result.success:
            detail = f"output={_preview(event.result.output, max_chars)}"
        else:
            detail = f"error={_preview(event.result.error, max_chars)}"
        return (
            f"step {event.step}: tool result {event.tool_call.tool_name} "
            f"success={event.result.success} {detail}"
        )
    return f"step {event.step}: final answer {_preview(event.final_answer, max_chars)}"


def _preview(value: Any, max_chars: int) -> str:
    rendered = json.dumps(_redact(value), default=str)
    if len(rendered) <= max_chars:
        return rendered
    return rendered[:max_chars] + "..."


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): "***" if _is_secret_key(str(key)) else _redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, str):
        return _API_KEY_TEXT.sub("***", value)
    return value


def _is_secret_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return any(marker in normalized for marker in _SECRET_MARKERS)
