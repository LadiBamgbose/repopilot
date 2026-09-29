"""Minimal agent orchestration loop."""

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

    The model client keeps provider conversation state. Tool failures are
    passed back as ``ToolResult`` observations. The loop stops on a final
    answer or when ``max_steps`` is reached.
    """
    response = llm.start(task)

    for step in range(1, max_steps + 1):
        if not isinstance(response, ToolCallResponse):
            return AgentResult(
                success=True,
                final_answer=response.final_answer,
                steps=step,
            )

        tool_result = execute_tool(response.tool_call, workspace=workspace)
        if step == max_steps:
            break
        response = llm.continue_with_tool_result(tool_result)

    return AgentResult(
        success=False,
        error=f"Exceeded maximum steps ({max_steps}) without a final answer",
        steps=max_steps,
    )
