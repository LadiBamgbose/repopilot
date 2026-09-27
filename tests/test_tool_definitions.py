"""Tests for typed tool definitions and argument validation."""

from repopilot.core.tool_definition import tool_schema
from repopilot.core.tool_protocol import ToolCall
from repopilot.core.tool_registry import TOOL_REGISTRY, execute_tool
from repopilot.workspace import Workspace


def test_valid_arguments_execute_normally(tmp_path):
    (tmp_path / "hello.txt").write_text("Hello RepoPilot!", encoding="utf-8")
    workspace = Workspace(tmp_path)
    request = ToolCall(
        tool_name="read_file",
        arguments={"path": "hello.txt"},
    )

    result = execute_tool(request, workspace=workspace)

    assert result.success is True
    assert result.output == "Hello RepoPilot!"
    assert result.error is None


def test_missing_required_argument_fails_validation(tmp_path):
    workspace = Workspace(tmp_path)
    request = ToolCall(tool_name="read_file", arguments={})

    result = execute_tool(request, workspace=workspace)

    assert result.success is False
    assert result.error is not None
    assert "Invalid arguments for read_file" in result.error
    assert "path" in result.error


def test_unexpected_argument_fails_validation(tmp_path):
    workspace = Workspace(tmp_path)
    request = ToolCall(
        tool_name="list_files",
        arguments={"extra": "nope"},
    )

    result = execute_tool(request, workspace=workspace)

    assert result.success is False
    assert result.error is not None
    assert "Invalid arguments for list_files" in result.error


def test_wrong_argument_type_fails_validation(tmp_path):
    workspace = Workspace(tmp_path)
    request = ToolCall(
        tool_name="search_repo",
        arguments={"query": 12},
    )

    result = execute_tool(request, workspace=workspace)

    assert result.success is False
    assert result.error is not None
    assert "Invalid arguments for search_repo" in result.error


def test_unknown_tool_still_fails_cleanly(tmp_path):
    workspace = Workspace(tmp_path)
    request = ToolCall(tool_name="not_a_tool", arguments={})

    result = execute_tool(request, workspace=workspace)

    assert result.success is False
    assert result.error == "Unknown tool: not_a_tool"


def test_generated_schema_contains_tool_name_and_required_parameters():
    schema = tool_schema(TOOL_REGISTRY["read_file"])

    assert schema["name"] == "read_file"
    assert schema["description"]
    assert schema["parameters"]["type"] == "object"
    assert "path" in schema["parameters"]["required"]
    assert "path" in schema["parameters"]["properties"]


def test_zero_argument_tool_generates_empty_object_schema():
    schema = tool_schema(TOOL_REGISTRY["list_files"])

    assert schema["name"] == "list_files"
    assert schema["parameters"]["type"] == "object"
    assert schema["parameters"].get("properties", {}) == {}
    assert schema["parameters"].get("required", []) == []

    run_tests_schema = tool_schema(TOOL_REGISTRY["run_tests"])
    assert run_tests_schema["parameters"]["type"] == "object"
    assert run_tests_schema["parameters"].get("properties", {}) == {}
    assert run_tests_schema["parameters"].get("required", []) == []
