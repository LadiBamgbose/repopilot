"""Repository workspace for tool execution."""

from pathlib import Path


class Workspace:
    """A single resolved repository root shared by tools."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
