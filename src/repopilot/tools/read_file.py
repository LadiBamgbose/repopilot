"""Read a UTF-8 text file from the repository."""

from repopilot.core.tool_protocol import ToolResult
from repopilot.workspace import Workspace


def read_file(path: str, *, workspace: Workspace) -> ToolResult:
    """Read a UTF-8 text file at a path relative to the workspace root.

    Paths that resolve outside the workspace root are rejected so callers
    cannot escape the workspace. Expected filesystem failures are returned as
    ToolResult errors rather than raised.
    """
    root = workspace.root
    resolved = (root / path).resolve()

    if not resolved.is_relative_to(root):
        return ToolResult(
            success=False,
            error=f"Path escapes the repository: {path}",
        )

    try:
        contents = resolved.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ToolResult(success=False, error=f"File not found: {path}")
    except PermissionError:
        return ToolResult(success=False, error=f"Permission denied: {path}")
    except UnicodeDecodeError:
        return ToolResult(success=False, error=f"Invalid UTF-8: {path}")
    except OSError as exc:
        return ToolResult(
            success=False,
            error=f"Filesystem error reading {path}: {exc}",
        )

    return ToolResult(success=True, output=contents)
