"""Tests for tool registry dispatch."""

from repopilot.core.tool_protocol import ToolCall
from repopilot.core.tool_registry import execute_tool
from repopilot.workspace import Workspace


def test_execute_tool_dispatches_read_file(tmp_path):
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


def test_execute_tool_dispatches_list_files(tmp_path):
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    workspace = Workspace(tmp_path)
    request = ToolCall(tool_name="list_files", arguments={})

    result = execute_tool(request, workspace=workspace)

    assert result.success is True
    assert result.output == ["a.txt"]
    assert result.error is None


def test_execute_tool_unknown_tool(tmp_path):
    workspace = Workspace(tmp_path)
    request = ToolCall(tool_name="not_a_tool", arguments={})

    result = execute_tool(request, workspace=workspace)

    assert result.success is False
    assert result.error == "Unknown tool: not_a_tool"
