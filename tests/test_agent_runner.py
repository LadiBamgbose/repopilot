"""Tests for the minimal agent orchestration loop."""

from repopilot.agent.runner import run_agent
from repopilot.agent.schemas import AgentResponse, FinalAnswerResponse, ToolCallResponse
from repopilot.core.tool_protocol import ToolCall, ToolResult
from repopilot.workspace import Workspace


class ScriptedLLM:
    """Deterministic fake LLM that returns a fixed sequence of responses."""

    def __init__(self, responses: list[AgentResponse]) -> None:
        self._responses = list(responses)
        self.started_task: str | None = None
        self.tool_results: list[ToolResult] = []

    def start(self, task: str) -> AgentResponse:
        self.started_task = task
        return self._next()

    def continue_with_tool_result(self, tool_result: ToolResult) -> AgentResponse:
        self.tool_results.append(tool_result)
        return self._next()

    def _next(self) -> AgentResponse:
        if not self._responses:
            raise AssertionError("ScriptedLLM has no remaining responses")
        return self._responses.pop(0)


def test_run_agent_immediate_final_answer(tmp_path):
    workspace = Workspace(tmp_path)
    llm = ScriptedLLM(
        [FinalAnswerResponse(final_answer="already done")]
    )

    result = run_agent("summarize the repo", llm=llm, workspace=workspace)

    assert result.success is True
    assert result.final_answer == "already done"
    assert result.error is None
    assert result.steps == 1
    assert llm.started_task == "summarize the repo"
    assert llm.tool_results == []


def test_run_agent_tool_then_final_answer(tmp_path):
    (tmp_path / "readme.txt").write_text("hello", encoding="utf-8")
    workspace = Workspace(tmp_path)
    llm = ScriptedLLM(
        [
            ToolCallResponse(
                tool_call=ToolCall(
                    tool_name="read_file",
                    arguments={"path": "readme.txt"},
                ),
            ),
            FinalAnswerResponse(final_answer="readme says hello"),
        ]
    )

    result = run_agent("read the readme", llm=llm, workspace=workspace)

    assert result.success is True
    assert result.final_answer == "readme says hello"
    assert result.steps == 2
    assert len(llm.tool_results) == 1
    assert llm.tool_results[0].success is True
    assert llm.tool_results[0].output == "hello"


def test_run_agent_multiple_tool_calls(tmp_path):
    (tmp_path / "a.txt").write_text("A", encoding="utf-8")
    (tmp_path / "b.txt").write_text("B", encoding="utf-8")
    workspace = Workspace(tmp_path)
    llm = ScriptedLLM(
        [
            ToolCallResponse(
                tool_call=ToolCall(
                    tool_name="read_file",
                    arguments={"path": "a.txt"},
                ),
            ),
            ToolCallResponse(
                tool_call=ToolCall(
                    tool_name="read_file",
                    arguments={"path": "b.txt"},
                ),
            ),
            FinalAnswerResponse(final_answer="A then B"),
        ]
    )

    result = run_agent("read both files", llm=llm, workspace=workspace)

    assert result.success is True
    assert result.final_answer == "A then B"
    assert result.steps == 3
    assert [item.output for item in llm.tool_results] == ["A", "B"]


def test_run_agent_failed_tool_result_continues(tmp_path):
    (tmp_path / "fallback.txt").write_text("fallback", encoding="utf-8")
    workspace = Workspace(tmp_path)
    llm = ScriptedLLM(
        [
            ToolCallResponse(
                tool_call=ToolCall(
                    tool_name="read_file",
                    arguments={"path": "missing.txt"},
                ),
            ),
            ToolCallResponse(
                tool_call=ToolCall(
                    tool_name="read_file",
                    arguments={"path": "fallback.txt"},
                ),
            ),
            FinalAnswerResponse(final_answer="used fallback"),
        ]
    )

    result = run_agent("find a file", llm=llm, workspace=workspace)

    assert result.success is True
    assert result.final_answer == "used fallback"
    assert result.steps == 3
    assert llm.tool_results[0].success is False
    assert llm.tool_results[0].error == "File not found: missing.txt"
    assert llm.tool_results[1].success is True
    assert llm.tool_results[1].output == "fallback"


def test_run_agent_max_steps_prevents_infinite_loop(tmp_path):
    workspace = Workspace(tmp_path)
    endless_tool = ToolCallResponse(
        tool_call=ToolCall(tool_name="list_files", arguments={}),
    )
    llm = ScriptedLLM([endless_tool for _ in range(3)])

    result = run_agent(
        "never finish",
        llm=llm,
        workspace=workspace,
        max_steps=3,
    )

    assert result.success is False
    assert result.final_answer is None
    assert "Exceeded maximum steps (3)" in result.error
    assert result.steps == 3
    assert len(llm.tool_results) == 2
