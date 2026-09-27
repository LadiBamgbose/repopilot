"""Schemas for agent actions and run outcomes."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from repopilot.core.tool_protocol import ToolCall


class ToolCallResponse(BaseModel):
    """Model action that requests a single tool invocation."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["tool_call"] = "tool_call"
    tool_call: ToolCall


class FinalAnswerResponse(BaseModel):
    """Model action that ends the loop with a final answer."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["final_answer"] = "final_answer"
    final_answer: str


AgentResponse = Annotated[
    ToolCallResponse | FinalAnswerResponse,
    Field(discriminator="type"),
]


class AgentResult(BaseModel):
    """Outcome returned by the agent loop."""

    success: bool
    final_answer: str | None = None
    error: str | None = None
    steps: int = 0
