"""Tests for the OpenAI Responses API client."""

import json
from types import SimpleNamespace

import pytest
from openai import OpenAIError

from repopilot.agent.schemas import FinalAnswerResponse, ToolCallResponse
from repopilot.core.tool_definition import tool_schema
from repopilot.core.tool_protocol import ToolResult
from repopilot.core.tool_registry import TOOL_REGISTRY
from repopilot.llm.openai_client import (
    LLMProviderError,
    LLMResponseError,
    OpenAIClient,
)
from repopilot.llm.openai_tools import to_openai_function_tool


class FakeResponses:
    def __init__(self, results: list[object]) -> None:
        self._results = list(results)
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        result = self._results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


class FakeSDK:
    def __init__(self, results: list[object]) -> None:
        self.responses = FakeResponses(results)


def _function_call(name: str, arguments: str, call_id: str) -> SimpleNamespace:
    return SimpleNamespace(
        type="function_call",
        name=name,
        arguments=arguments,
        call_id=call_id,
    )


def _api_response(
    response_id: str,
    *,
    function_call: SimpleNamespace | None = None,
    text: str | None = None,
) -> SimpleNamespace:
    output = [function_call] if function_call is not None else []
    return SimpleNamespace(id=response_id, output_text=text, output=output)


def test_start_sends_only_the_initial_task():
    sdk = FakeSDK([_api_response("resp_1", text="ok")])
    client = OpenAIClient(model="gpt-test", client=sdk)

    client.start("read the repo")

    request = sdk.responses.calls[0]
    assert request["input"] == [{"role": "user", "content": "read the repo"}]
    assert "previous_response_id" not in request
    assert request["model"] == "gpt-test"
    assert request["parallel_tool_calls"] is False


def test_start_stores_response_id_and_exact_call_id():
    sdk = FakeSDK(
        [
            _api_response(
                "resp_1",
                function_call=_function_call("read_file", '{"path": "a.py"}', "call_abc"),
            )
        ]
    )
    client = OpenAIClient(model="gpt-test", client=sdk)
    client._previous_response_id = "old-response"
    client._pending_call_id = "old-call"

    response = client.start("read a.py")

    assert isinstance(response, ToolCallResponse)
    assert response.tool_call.tool_name == "read_file"
    assert response.tool_call.arguments == {"path": "a.py"}
    assert client._previous_response_id == "resp_1"
    assert client._pending_call_id == "call_abc"


def test_continue_sends_only_the_new_function_output():
    first = _api_response(
        "resp_1",
        function_call=_function_call("read_file", '{"path": "a.py"}', "call_abc"),
    )
    second = _api_response(
        "resp_2",
        function_call=_function_call("list_files", "{}", "call_next"),
    )
    sdk = FakeSDK([first, second])
    client = OpenAIClient(model="gpt-test", client=sdk)
    client.start("inspect")

    tool_result = ToolResult(success=True, output="hello")
    response = client.continue_with_tool_result(tool_result)

    request = sdk.responses.calls[1]
    assert request["previous_response_id"] == "resp_1"
    assert request["input"] == [
        {
            "type": "function_call_output",
            "call_id": "call_abc",
            "output": json.dumps(tool_result.model_dump()),
        }
    ]
    assert isinstance(response, ToolCallResponse)
    assert client._previous_response_id == "resp_2"
    assert client._pending_call_id == "call_next"


def test_final_answer_clears_pending_call_id():
    sdk = FakeSDK(
        [
            _api_response(
                "resp_1",
                function_call=_function_call("read_file", '{"path": "a.py"}', "call_abc"),
            ),
            _api_response("resp_2", text="all done"),
        ]
    )
    client = OpenAIClient(model="gpt-test", client=sdk)
    client.start("read a.py")

    response = client.continue_with_tool_result(ToolResult(success=True, output="hello"))

    assert isinstance(response, FinalAnswerResponse)
    assert response.final_answer == "all done"
    assert client._previous_response_id == "resp_2"
    assert client._pending_call_id is None


def test_tool_definitions_come_from_registry_schemas():
    sdk = FakeSDK([_api_response("resp_1", text="ok")])
    client = OpenAIClient(model="gpt-test", client=sdk)

    client.start("hi")

    tools = sdk.responses.calls[0]["tools"]
    by_name = {tool["name"]: tool for tool in tools}
    assert set(by_name) == set(TOOL_REGISTRY)
    read_file = by_name["read_file"]
    assert read_file == to_openai_function_tool(TOOL_REGISTRY["read_file"])
    assert read_file["parameters"] == tool_schema(TOOL_REGISTRY["read_file"])["parameters"]
    assert "path" in read_file["parameters"]["required"]


def test_malformed_tool_arguments_fail_cleanly():
    sdk = FakeSDK(
        [
            _api_response(
                "resp_1",
                function_call=_function_call("read_file", "{not-json", "call_abc"),
            )
        ]
    )
    client = OpenAIClient(model="gpt-test", client=sdk)

    with pytest.raises(LLMResponseError, match="Malformed tool arguments"):
        client.start("read a.py")


def test_provider_exception_is_not_swallowed():
    sdk = FakeSDK([OpenAIError("network down")])
    client = OpenAIClient(model="gpt-test", client=sdk)

    with pytest.raises(LLMProviderError, match="network down"):
        client.start("hi")


def test_continue_without_active_response_or_call_fails():
    sdk = FakeSDK([])
    client = OpenAIClient(model="gpt-test", client=sdk)
    observation = ToolResult(success=True, output="hello")

    with pytest.raises(LLMResponseError, match="No active OpenAI response"):
        client.continue_with_tool_result(observation)

    client._previous_response_id = "resp_1"
    with pytest.raises(LLMResponseError, match="No pending OpenAI function call"):
        client.continue_with_tool_result(observation)
