"""Shared schemas for agent tool invocation and results."""

from typing import Any

from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    """Structured request for a single tool invocation.

    The agent produces tool calls as JSON-like payloads. This model gives those
    calls a typed, validated shape so runners can dispatch work without parsing
    ad hoc dictionaries or guessing argument structure.
    """

    tool_name: str
    arguments: dict[str, Any]


class ToolResult(BaseModel):
    """Normalized outcome returned after a tool runs.

    Every tool reports success or failure through the same fields, which keeps
    logging, retries, and agent reasoning consistent regardless of which tool ran.
    """

    success: bool
    output: Any | None = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    duration_ms: int | None = None
