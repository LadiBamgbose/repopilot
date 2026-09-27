"""Tool metadata used by the registry and future model clients."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from repopilot.core.tool_protocol import ToolResult


@dataclass(frozen=True)
class ToolDefinition:
    """One executable tool plus the schema that validates its arguments."""

    name: str
    description: str
    function: Callable[..., ToolResult]
    args_model: type[BaseModel]


def tool_schema(definition: ToolDefinition) -> dict[str, Any]:
    """Return provider-neutral metadata for a tool.

    ``parameters`` is the JSON schema produced by the tool's argument model.
    """
    return {
        "name": definition.name,
        "description": definition.description,
        "parameters": definition.args_model.model_json_schema(),
    }
