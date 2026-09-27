"""Tests for agent response schema validation."""

import pytest
from pydantic import TypeAdapter, ValidationError

from repopilot.agent.schemas import (
    AgentResponse,
    FinalAnswerResponse,
    ToolCallResponse,
)
from repopilot.core.tool_protocol import ToolCall

adapter = TypeAdapter(AgentResponse)


def test_agent_response_accepts_tool_call():
    response = adapter.validate_python(
        {
            "type": "tool_call",
            "tool_call": {
                "tool_name": "read_file",
                "arguments": {"path": "a.py"},
            },
        }
    )

    assert isinstance(response, ToolCallResponse)
    assert response.type == "tool_call"
    assert response.tool_call.tool_name == "read_file"


def test_agent_response_accepts_final_answer():
    response = adapter.validate_python(
        {"type": "final_answer", "final_answer": "done"}
    )

    assert isinstance(response, FinalAnswerResponse)
    assert response.type == "final_answer"
    assert response.final_answer == "done"


def test_agent_response_rejects_tool_call_without_payload():
    with pytest.raises(ValidationError):
        adapter.validate_python({"type": "tool_call"})


def test_agent_response_rejects_final_answer_without_text():
    with pytest.raises(ValidationError):
        adapter.validate_python({"type": "final_answer"})


def test_agent_response_rejects_both_actions_on_tool_call():
    with pytest.raises(ValidationError):
        adapter.validate_python(
            {
                "type": "tool_call",
                "tool_call": {
                    "tool_name": "list_files",
                    "arguments": {},
                },
                "final_answer": "also an answer",
            }
        )


def test_agent_response_rejects_both_actions_on_final_answer():
    with pytest.raises(ValidationError):
        adapter.validate_python(
            {
                "type": "final_answer",
                "final_answer": "done",
                "tool_call": {
                    "tool_name": "list_files",
                    "arguments": {},
                },
            }
        )


def test_concrete_response_models_are_constructible():
    tool = ToolCallResponse(
        tool_call=ToolCall(tool_name="list_files", arguments={}),
    )
    answer = FinalAnswerResponse(final_answer="done")

    assert tool.type == "tool_call"
    assert answer.type == "final_answer"
