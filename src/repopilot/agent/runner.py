"""Minimal agent orchestration loop."""

from typing import Any

from repopilot.agent.schemas import AgentResult, ToolCallResponse
from repopilot.core.tool_registry import execute_tool
from repopilot.llm.client import LLMClient
from repopilot.workspace import Workspace

MAX_STEPS = 20


def run_agent(
    task: str,
    *,
    llm: LLMClient,
    workspace: Workspace,
    max_steps: int = MAX_STEPS,
) -> AgentResult:
    """Run a task by alternating LLM decisions and tool executions.

    History includes the original task, each model tool call, and each
    ``ToolResult`` (including failures). The loop stops on a final answer or
    when ``max_steps`` is reached.
    """
    messages: list[dict[str, Any]] = [
        {"role": "user", "content": task},
    ]

    for step in range(1, max_steps + 1):
        response = llm.respond(messages)

        if isinstance(response, ToolCallResponse):
            messages.append(
                {
                    "role": "assistant",
                    "type": "tool_call",
                    "tool_call": response.tool_call.model_dump(),
                }
            )

            tool_result = execute_tool(response.tool_call, workspace=workspace)
            messages.append(
                {
                    "role": "tool",
                    "tool_result": tool_result.model_dump(),
                }
            )
            continue

        return AgentResult(
            success=True,
            final_answer=response.final_answer,
            steps=step,
        )

    return AgentResult(
        success=False,
        error=f"Exceeded maximum steps ({max_steps}) without a final answer",
        steps=max_steps,
    )
