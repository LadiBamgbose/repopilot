"""Dispatch ToolCall payloads to registered tools."""

from pydantic import ValidationError

from repopilot.core.tool_definition import ToolDefinition
from repopilot.core.tool_protocol import ToolCall, ToolResult
from repopilot.tools.list_files import ListFilesArgs, list_files
from repopilot.tools.read_file import ReadFileArgs, read_file
from repopilot.tools.run_tests import RunTestsArgs, run_tests
from repopilot.tools.search_repo import SearchRepoArgs, search_repo
from repopilot.tools.write_file import WriteFileArgs, write_file
from repopilot.workspace import Workspace

TOOL_REGISTRY = {
    "list_files": ToolDefinition(
        name="list_files",
        description="Recursively list files under the workspace root.",
        function=list_files,
        args_model=ListFilesArgs,
    ),
    "read_file": ToolDefinition(
        name="read_file",
        description="Read a UTF-8 text file relative to the workspace root.",
        function=read_file,
        args_model=ReadFileArgs,
    ),
    "run_tests": ToolDefinition(
        name="run_tests",
        description="Run the workspace pytest suite.",
        function=run_tests,
        args_model=RunTestsArgs,
    ),
    "search_repo": ToolDefinition(
        name="search_repo",
        description="Search UTF-8 files under the workspace root for a substring.",
        function=search_repo,
        args_model=SearchRepoArgs,
    ),
    "write_file": ToolDefinition(
        name="write_file",
        description="Overwrite an existing UTF-8 text file in the workspace.",
        function=write_file,
        args_model=WriteFileArgs,
    ),
}


def execute_tool(request: ToolCall, *, workspace: Workspace) -> ToolResult:
    definition = TOOL_REGISTRY.get(request.tool_name)
    if definition is None:
        return ToolResult(
            success=False,
            error=f"Unknown tool: {request.tool_name}",
        )

    try:
        validated = definition.args_model.model_validate(request.arguments)
    except ValidationError as exc:
        return ToolResult(
            success=False,
            error=f"Invalid arguments for {request.tool_name}: {exc}",
        )

    return definition.function(**validated.model_dump(), workspace=workspace)
