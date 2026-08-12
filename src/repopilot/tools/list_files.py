"""List files in the repository workspace."""

from repopilot.core.tool_protocol import ToolResult
from repopilot.workspace import Workspace

_IGNORED_NAMES = frozenset({".git", ".venv", "__pycache__", ".pytest_cache"})


def list_files(*, workspace: Workspace) -> ToolResult:
    """Recursively list files under the workspace root.

    Paths are returned relative to ``workspace.root``. Directories named in
    ``_IGNORED_NAMES`` are skipped. Expected filesystem failures are returned
    as ToolResult errors rather than raised.
    """
    root = workspace.root
    files: list[str] = []

    try:
        for path in root.rglob("*"):
            resolved = path.resolve()
            if not resolved.is_relative_to(root):
                continue
            if not resolved.is_file():
                continue
            relative = resolved.relative_to(root)
            if any(part in _IGNORED_NAMES for part in relative.parts):
                continue
            files.append(relative.as_posix())
    except OSError as exc:
        return ToolResult(
            success=False,
            error=f"Filesystem error listing files: {exc}",
        )

    files.sort()
    return ToolResult(success=True, output=files)
