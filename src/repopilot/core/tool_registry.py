"""Dispatch ToolCall payloads to registered tools."""

from repopilot.core.tool_protocol import ToolCall, ToolResult
from repopilot.tools.list_files import list_files
from repopilot.tools.read_file import read_file
from repopilot.workspace import Workspace

TOOL_REGISTRY = {
    "list_files": list_files,
    "read_file": read_file,
}


def execute_tool(request: ToolCall, *, workspace: Workspace) -> ToolResult:
    tool = TOOL_REGISTRY.get(request.tool_name)
    if tool is None:
        return ToolResult(
            success=False,
            error=f"Unknown tool: {request.tool_name}",
        )

    return tool(**request.arguments, workspace=workspace)
