"""Minimal LLM interface for the agent loop."""

from typing import Any, Protocol

from repopilot.agent.schemas import AgentResponse


class LLMClient(Protocol):
    """Provider-agnostic model interface used by the agent runner.

    Implementations receive the full conversation history and return the next
    structured action. Concrete providers (OpenAI, Anthropic, etc.) can be
    added later without changing the orchestration loop.
    """

    def respond(self, messages: list[dict[str, Any]]) -> AgentResponse:
        """Return the next tool call or final answer for ``messages``."""
        ...
