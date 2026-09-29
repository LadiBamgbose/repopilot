"""Minimal agent orchestration loop."""

from repopilot.agent.observer import (
    AgentEvent,
    AgentObserver,
    FinalAnswerReached,
    ModelResponseReceived,
    ToolCallRequested,
    ToolResultReturned,
)
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
    observer: AgentObserver | None = None,
) -> AgentResult:
    """Run a task by alternating LLM decisions and tool executions.

    The model client keeps provider conversation state. Tool failures are
    passed back as ``ToolResult`` observations. The loop stops on a final
    answer or when ``max_steps`` is reached. ``observer`` receives those
    steps when provided; the default run stays quiet.
    """
    response = llm.start(task)

    for step in range(1, max_steps + 1):
        _emit(observer, ModelResponseReceived(step=step, response=response))
        if not isinstance(response, ToolCallResponse):
            _emit(
                observer,
                FinalAnswerReached(step=step, final_answer=response.final_answer),
            )
            return AgentResult(
                success=True,
                final_answer=response.final_answer,
                steps=step,
            )

        _emit(observer, ToolCallRequested(step=step, tool_call=response.tool_call))
        tool_result = execute_tool(response.tool_call, workspace=workspace)
        _emit(
            observer,
            ToolResultReturned(
                step=step,
                tool_call=response.tool_call,
                result=tool_result,
            ),
        )
        if step == max_steps:
            break
        response = llm.continue_with_tool_result(tool_result)

    return AgentResult(
        success=False,
        error=f"Exceeded maximum steps ({max_steps}) without a final answer",
        steps=max_steps,
    )


def _emit(observer: AgentObserver | None, event: AgentEvent) -> None:
    if observer is not None:
        observer.on_event(event)
