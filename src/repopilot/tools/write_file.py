"""Overwrite a UTF-8 text file in the repository."""

from repopilot.core.tool_protocol import ToolResult
from repopilot.workspace import Workspace


def write_file(
    path: str,
    contents: str,
    *,
    workspace: Workspace,
) -> ToolResult:
    """Overwrite an existing UTF-8 text file relative to the workspace root.

    Paths that resolve outside the workspace root are rejected so callers
    cannot escape the workspace. Missing files and directories are not
    created. Expected filesystem failures are returned as ToolResult errors
    rather than raised.
    """
    root = workspace.root
    resolved = (root / path).resolve()

    if not resolved.is_relative_to(root):
        return ToolResult(
            success=False,
            error=f"Path escapes the repository: {path}",
        )

    if resolved.is_dir():
        return ToolResult(success=False, error=f"Is a directory: {path}")

    if not resolved.exists():
        return ToolResult(success=False, error=f"File not found: {path}")

    encoded = contents.encode("utf-8")
    try:
        resolved.write_bytes(encoded)
    except PermissionError:
        return ToolResult(success=False, error=f"Permission denied: {path}")
    except OSError as exc:
        return ToolResult(
            success=False,
            error=f"Filesystem error writing {path}: {exc}",
        )

    return ToolResult(
        success=True,
        output={
            "path": resolved.relative_to(root).as_posix(),
            "bytes_written": len(encoded),
        },
    )
