"""Tests for agent-loop observer callbacks."""

from repopilot.agent.observer import (
    ConsoleAgentObserver,
    FinalAnswerReached,
    ModelResponseReceived,
    ToolCallRequested,
    ToolResultReturned,
)
from repopilot.agent.runner import run_agent
from repopilot.agent.schemas import AgentResponse, FinalAnswerResponse, ToolCallResponse
from repopilot.core.tool_protocol import ToolCall, ToolResult
from repopilot.workspace import Workspace


class ScriptedLLM:
    """Deterministic fake LLM that returns a fixed sequence of responses."""

    def __init__(self, responses: list[AgentResponse]) -> None:
        self._responses = list(responses)

    def start(self, task: str) -> AgentResponse:
        return self._next()

    def continue_with_tool_result(self, tool_result: ToolResult) -> AgentResponse:
        return self._next()

    def _next(self) -> AgentResponse:
        if not self._responses:
            raise AssertionError("ScriptedLLM has no remaining responses")
        return self._responses.pop(0)


class RecordingObserver:
    def __init__(self) -> None:
        self.events: list[object] = []

    def on_event(self, event: object) -> None:
        self.events.append(event)


def _read(path: str) -> ToolCallResponse:
    return ToolCallResponse(
        tool_call=ToolCall(tool_name="read_file", arguments={"path": path}),
    )


def test_observer_immediate_final_answer(tmp_path):
    observer = RecordingObserver()
    result = run_agent(
        "summarize",
        llm=ScriptedLLM([FinalAnswerResponse(final_answer="done")]),
        workspace=Workspace(tmp_path),
        observer=observer,
    )

    assert result.success is True
    assert [type(event) for event in observer.events] == [
        ModelResponseReceived,
        FinalAnswerReached,
    ]
    assert [event.step for event in observer.events] == [1, 1]
    assert observer.events[1].final_answer == "done"


def test_observer_tool_then_final_answer_order(tmp_path):
    (tmp_path / "readme.txt").write_text("hello", encoding="utf-8")
    observer = RecordingObserver()

    result = run_agent(
        "read the readme",
        llm=ScriptedLLM(
            [
                _read("readme.txt"),
                FinalAnswerResponse(final_answer="readme says hello"),
            ]
        ),
        workspace=Workspace(tmp_path),
        observer=observer,
    )

    assert result.success is True
    assert [type(event) for event in observer.events] == [
        ModelResponseReceived,
        ToolCallRequested,
        ToolResultReturned,
        ModelResponseReceived,
        FinalAnswerReached,
    ]
    assert [event.step for event in observer.events] == [1, 1, 1, 2, 2]
    assert observer.events[1].tool_call.tool_name == "read_file"
    assert observer.events[1].tool_call.arguments == {"path": "readme.txt"}
    assert observer.events[2].result.success is True
    assert observer.events[2].result.output == "hello"
    assert observer.events[4].final_answer == "readme says hello"


def test_observer_failed_tool_then_recovery(tmp_path):
    (tmp_path / "fallback.txt").write_text("fallback", encoding="utf-8")
    observer = RecordingObserver()

    run_agent(
        "find a file",
        llm=ScriptedLLM(
            [
                _read("missing.txt"),
                _read("fallback.txt"),
                FinalAnswerResponse(final_answer="used fallback"),
            ]
        ),
        workspace=Workspace(tmp_path),
        observer=observer,
    )

    tool_results = [
        event for event in observer.events if isinstance(event, ToolResultReturned)
    ]
    assert [event.result.success for event in tool_results] == [False, True]
    assert tool_results[0].result.error == "File not found: missing.txt"
    assert tool_results[1].result.output == "fallback"
    assert isinstance(observer.events[-1], FinalAnswerReached)
    assert [event.step for event in observer.events] == [1, 1, 1, 2, 2, 2, 3, 3]


def test_observer_max_steps_has_no_final_answer(tmp_path):
    observer = RecordingObserver()
    tool_call = ToolCallResponse(
        tool_call=ToolCall(tool_name="list_files", arguments={}),
    )

    result = run_agent(
        "never finish",
        llm=ScriptedLLM([tool_call for _ in range(3)]),
        workspace=Workspace(tmp_path),
        max_steps=3,
        observer=observer,
    )

    assert result.success is False
    assert [type(event) for event in observer.events] == [
        ModelResponseReceived,
        ToolCallRequested,
        ToolResultReturned,
    ] * 3
    assert [event.step for event in observer.events] == [1, 1, 1, 2, 2, 2, 3, 3, 3]
    assert not any(isinstance(event, FinalAnswerReached) for event in observer.events)


def test_run_without_observer_stays_quiet(tmp_path, capsys):
    (tmp_path / "readme.txt").write_text("hello", encoding="utf-8")
    run_agent(
        "read the readme",
        llm=ScriptedLLM(
            [
                _read("readme.txt"),
                FinalAnswerResponse(final_answer="readme says hello"),
            ]
        ),
        workspace=Workspace(tmp_path),
    )

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_console_observer_truncates_output_and_hides_secrets(capsys):
    secret = "sk-supersecretvalue12"
    contents = ("A" * 80) + "ENDMARKER"
    observer = ConsoleAgentObserver(max_chars=40)
    observer.on_event(
        ToolCallRequested(
            step=1,
            tool_call=ToolCall(
                tool_name="write_file",
                arguments={"path": "a.py", "api_key": secret, "contents": "x"},
            ),
        )
    )
    observer.on_event(
        ToolResultReturned(
            step=2,
            tool_call=ToolCall(tool_name="read_file", arguments={"path": "big.txt"}),
            result=ToolResult(success=True, output=f"prefix {secret} {contents}"),
        )
    )
    observer.on_event(FinalAnswerReached(step=3, final_answer="fixed"))

    output = capsys.readouterr().out
    assert secret not in output
    assert "ENDMARKER" not in output
    assert "api_key" in output
    assert '"***"' in output
    assert "step 1: tool call write_file" in output
    assert "step 2: tool result read_file success=True" in output
    assert "step 3: final answer" in output
    assert "..." in output
