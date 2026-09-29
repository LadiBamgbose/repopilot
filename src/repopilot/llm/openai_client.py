"""OpenAI Responses API client for the agent loop."""

import json
from collections.abc import Mapping
from typing import Any

from openai import OpenAI, OpenAIError

from repopilot.agent.schemas import AgentResponse, FinalAnswerResponse, ToolCallResponse
from repopilot.core.tool_definition import ToolDefinition
from repopilot.core.tool_protocol import ToolCall, ToolResult
from repopilot.core.tool_registry import TOOL_REGISTRY
from repopilot.llm.openai_tools import to_openai_function_tools


class LLMProviderError(Exception):
    """The OpenAI API request failed."""


class LLMResponseError(Exception):
    """The OpenAI response could not be converted into an AgentResponse."""


class OpenAIClient:
    """Talk to the Responses API for one active agent run.

    This client does not execute tools. It tracks the latest OpenAI response
    id and function ``call_id`` so the next turn can continue incrementally.
    """

    def __init__(
        self,
        *,
        model: str,
        client: Any | None = None,
        tools: Mapping[str, ToolDefinition] | None = None,
    ) -> None:
        self.model = model
        self._client = client if client is not None else OpenAI()
        self._tools = dict(tools) if tools is not None else dict(TOOL_REGISTRY)
        self._previous_response_id: str | None = None
        self._pending_call_id: str | None = None

    def start(self, task: str) -> AgentResponse:
        """Begin a new run from a single user task."""
        self._previous_response_id = None
        self._pending_call_id = None
        return self._complete_turn(input=_task_input(task))

    def continue_with_tool_result(self, tool_result: ToolResult) -> AgentResponse:
        """Send one tool observation for the pending OpenAI function call."""
        if self._previous_response_id is None:
            raise LLMResponseError("No active OpenAI response to continue")
        if self._pending_call_id is None:
            raise LLMResponseError("No pending OpenAI function call to continue")

        return self._complete_turn(
            input=_tool_result_input(self._pending_call_id, tool_result),
            previous_response_id=self._previous_response_id,
        )

    def _complete_turn(
        self,
        *,
        input: list[dict[str, Any]],
        previous_response_id: str | None = None,
    ) -> AgentResponse:
        request: dict[str, Any] = {
            "model": self.model,
            "input": input,
            "tools": to_openai_function_tools(list(self._tools.values())),
            # The runner executes one tool per step and answers one call id.
            "parallel_tool_calls": False,
        }
        if previous_response_id is not None:
            request["previous_response_id"] = previous_response_id

        try:
            response = self._client.responses.create(**request)
        except OpenAIError as exc:
            raise LLMProviderError(str(exc)) from exc

        response_id = getattr(response, "id", None)
        if not isinstance(response_id, str) or not response_id:
            raise LLMResponseError("OpenAI response is missing an id")

        agent_response, call_id = _parse_response(response)
        self._previous_response_id = response_id
        self._pending_call_id = call_id
        return agent_response


def _task_input(task: str) -> list[dict[str, Any]]:
    """Convert the initial task into a Responses API user message."""
    return [{"role": "user", "content": task}]


def _tool_result_input(call_id: str, tool_result: ToolResult) -> list[dict[str, Any]]:
    """Convert one tool observation into a function_call_output item."""
    return [
        {
            "type": "function_call_output",
            "call_id": call_id,
            "output": json.dumps(tool_result.model_dump()),
        }
    ]


def _parse_response(response: Any) -> tuple[AgentResponse, str | None]:
    for item in getattr(response, "output", None) or []:
        if getattr(item, "type", None) == "function_call":
            call_id = getattr(item, "call_id", None)
            if not isinstance(call_id, str) or not call_id:
                raise LLMResponseError("OpenAI function call is missing a call_id")
            arguments = _parse_tool_arguments(getattr(item, "arguments", None))
            return (
                ToolCallResponse(
                    tool_call=ToolCall(
                        tool_name=item.name,
                        arguments=arguments,
                    )
                ),
                call_id,
            )

    text = _final_text(response)
    if text is None:
        raise LLMResponseError("Model response contained neither a tool call nor text")
    return FinalAnswerResponse(final_answer=text), None


def _parse_tool_arguments(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, str):
        raise LLMResponseError("Malformed tool arguments: expected a JSON string")
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LLMResponseError(f"Malformed tool arguments: {exc}") from exc
    if not isinstance(parsed, dict):
        raise LLMResponseError("Malformed tool arguments: expected a JSON object")
    return parsed


def _final_text(response: Any) -> str | None:
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text

    parts: list[str] = []
    for item in getattr(response, "output", None) or []:
        if getattr(item, "type", None) != "message":
            continue
        content = getattr(item, "content", None)
        if isinstance(content, str):
            parts.append(content)
            continue
        for block in content or []:
            text = getattr(block, "text", None)
            if isinstance(text, str):
                parts.append(text)
    combined = "".join(parts).strip()
    return combined or None
