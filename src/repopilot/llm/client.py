"""Minimal LLM interface for the agent loop."""

from typing import Protocol

from repopilot.agent.schemas import AgentResponse
from repopilot.core.tool_protocol import ToolResult


class LLMClient(Protocol):
    """Provider-agnostic model interface used by the agent runner.

    The client owns whatever conversation state its provider needs. The runner
    starts a task, then feeds back each tool result until the model finishes.
    """

    def start(self, task: str) -> AgentResponse:
        """Begin a run and return the first tool call or final answer."""
        ...

    def continue_with_tool_result(self, tool_result: ToolResult) -> AgentResponse:
        """Continue the active run after one tool observation."""
        ...
