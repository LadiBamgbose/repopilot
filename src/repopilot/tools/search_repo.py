"""Search the repository for matching text."""

from repopilot.core.tool_protocol import ToolResult
from repopilot.workspace import Workspace

_IGNORED_NAMES = frozenset({".git", ".venv", "__pycache__", ".pytest_cache"})


def search_repo(
    query: str,
    *,
    workspace: Workspace,
) -> ToolResult:
    """Search UTF-8 files under the workspace root for a substring.

    Matching is case-insensitive. Directories named in ``_IGNORED_NAMES`` are
    skipped. Invalid UTF-8 files are skipped rather than failing the search.
    Paths that resolve outside the workspace root are ignored so callers cannot
    escape the workspace.
    """
    root = workspace.root
    needle = query.lower()
    matches: list[dict[str, str | int]] = []

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

            try:
                text = resolved.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue

            relative_path = relative.as_posix()
            for line_number, line in enumerate(text.splitlines(), start=1):
                if needle in line.lower():
                    matches.append(
                        {
                            "path": relative_path,
                            "line_number": line_number,
                            "line": line,
                        }
                    )
    except OSError as exc:
        return ToolResult(
            success=False,
            error=f"Filesystem error searching files: {exc}",
        )

    matches.sort(key=lambda match: (match["path"], match["line_number"]))
    return ToolResult(success=True, output=matches)
