"""Tests for the deterministic benchmark harness."""

import tempfile
from pathlib import Path

from repopilot.agent.observer import (
    FinalAnswerReached,
    ModelResponseReceived,
    ToolCallRequested,
    ToolResultReturned,
)
from repopilot.agent.schemas import (
    AgentResponse,
    AgentResult,
    FinalAnswerResponse,
    ToolCallResponse,
)
from repopilot.core.tool_protocol import ToolCall, ToolResult
from repopilot.evals import benchmark_runner
from repopilot.evals.benchmark_runner import (
    BENCHMARK_FIXTURE_NAMES,
    default_benchmark_tasks,
    run_benchmark,
)
from repopilot.evals.metrics import summarize
from repopilot.evals.metrics_observer import BenchmarkMetricsObserver
from repopilot.evals.schemas import TaskEvalResult


BROKEN_SOURCE = "def value() -> int:\n    return 1\n"
FIXED_SOURCE = "def value() -> int:\n    return 2\n"
WIDGET_TEST = "from widget import value\n\n\ndef test_value():\n    assert value() == 2\n"


class ScriptedLLM:
    """Returns a prepared response list for each task prompt."""

    def __init__(self, responses_by_prompt: dict[str, list[AgentResponse]]) -> None:
        self._responses_by_prompt = responses_by_prompt
        self._queue: list[AgentResponse] = []
        self.started: list[str] = []
        self.tool_results: list[ToolResult] = []

    def start(self, task: str) -> AgentResponse:
        self.started.append(task)
        self._queue = list(self._responses_by_prompt[task])
        return self._next()

    def continue_with_tool_result(self, tool_result: ToolResult) -> AgentResponse:
        self.tool_results.append(tool_result)
        return self._next()

    def _next(self) -> AgentResponse:
        if not self._queue:
            raise AssertionError("ScriptedLLM has no remaining responses")
        return self._queue.pop(0)


def _write_fix() -> ToolCallResponse:
    return ToolCallResponse(
        tool_call=ToolCall(
            tool_name="write_file",
            arguments={"path": "widget.py", "contents": FIXED_SOURCE},
        )
    )


def _list_files() -> ToolCallResponse:
    return ToolCallResponse(
        tool_call=ToolCall(tool_name="list_files", arguments={}),
    )


def _read(path: str) -> ToolCallResponse:
    return ToolCallResponse(
        tool_call=ToolCall(tool_name="read_file", arguments={"path": path}),
    )


def _run_tests() -> ToolCallResponse:
    return ToolCallResponse(
        tool_call=ToolCall(tool_name="run_tests", arguments={}),
    )


def _make_fixture(root: Path, name: str, prompt: str) -> Path:
    fixture = root / name
    fixture.mkdir()
    (fixture / "widget.py").write_text(BROKEN_SOURCE, encoding="utf-8")
    (fixture / "test_widget.py").write_text(WIDGET_TEST, encoding="utf-8")
    (fixture / "pytest.ini").write_text("[pytest]\ntestpaths = .\n", encoding="utf-8")
    (fixture / "task.txt").write_text(prompt + "\n", encoding="utf-8")
    return fixture


def _snapshot(root: Path) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in {".pytest_cache", "__pycache__"} for part in path.parts):
            continue
        files[path.relative_to(root).as_posix()] = path.read_bytes()
    return files


def test_fixture_copy_leaves_source_unchanged_and_hides_prompt(tmp_path):
    prompt = "Fix widget.py so the test passes."
    fixture = _make_fixture(tmp_path, "widget_bug", prompt)
    before = _snapshot(fixture)
    llm = ScriptedLLM(
        {
            prompt: [
                _list_files(),
                _write_fix(),
                FinalAnswerResponse(final_answer="fixed"),
            ]
        }
    )

    summary = run_benchmark(
        [benchmark_runner.load_benchmark_task(fixture)],
        llm=llm,
    )

    assert llm.started == [prompt]
    assert "task.txt" not in llm.tool_results[0].output
    assert "widget.py" in llm.tool_results[0].output
    assert _snapshot(fixture) == before
    assert summary.results[0].tests_passed is True


def test_agent_success_does_not_imply_benchmark_success(tmp_path):
    prompt = "Fix widget.py so the test passes."
    fixture = _make_fixture(tmp_path, "widget_bug", prompt)
    llm = ScriptedLLM({prompt: [FinalAnswerResponse(final_answer="looks done")]})

    summary = run_benchmark(
        [benchmark_runner.load_benchmark_task(fixture)],
        llm=llm,
    )

    result = summary.results[0]
    assert result.agent_result.success is True
    assert result.tests_passed is False
    assert result.failure_reason == "Fixture tests failed (exit code 1)"
    assert (fixture / "widget.py").read_text(encoding="utf-8") == BROKEN_SOURCE


def test_pytest_determines_benchmark_success(tmp_path):
    prompt = "Fix widget.py so the test passes."
    fixture = _make_fixture(tmp_path, "widget_bug", prompt)
    llm = ScriptedLLM(
        {
            prompt: [
                _write_fix(),
                FinalAnswerResponse(final_answer="fixed"),
            ]
        }
    )

    summary = run_benchmark(
        [benchmark_runner.load_benchmark_task(fixture)],
        llm=llm,
    )

    result = summary.results[0]
    assert result.tests_passed is True
    assert result.failure_reason is None
    assert result.steps == 2
    assert result.agent_result.final_answer == "fixed"
    assert (fixture / "widget.py").read_text(encoding="utf-8") == BROKEN_SOURCE


def test_failed_agent_run_records_failure_reason(tmp_path):
    prompt = "Fix widget.py so the test passes."
    fixture = _make_fixture(tmp_path, "widget_bug", prompt)
    llm = ScriptedLLM({prompt: [_list_files()]})

    summary = run_benchmark(
        [benchmark_runner.load_benchmark_task(fixture)],
        llm=llm,
        max_steps=1,
    )

    result = summary.results[0]
    assert result.agent_result.success is False
    assert result.tests_passed is False
    assert result.failure_reason == "Exceeded maximum steps (1) without a final answer"
    assert result.steps == 1


def test_summary_metrics_cover_every_attempted_task(tmp_path):
    passing_prompt = "Fix the passing widget."
    failing_prompt = "Leave the failing widget."
    passing = benchmark_runner.load_benchmark_task(
        _make_fixture(tmp_path, "passing_bug", passing_prompt)
    )
    failing = benchmark_runner.load_benchmark_task(
        _make_fixture(tmp_path, "failing_bug", failing_prompt)
    )
    llm = ScriptedLLM(
        {
            passing_prompt: [
                _write_fix(),
                FinalAnswerResponse(final_answer="fixed"),
            ],
            failing_prompt: [FinalAnswerResponse(final_answer="unchanged")],
        }
    )

    summary = run_benchmark([passing, failing], llm=llm)

    assert summary.total_tasks == 2
    assert summary.tasks_passed == 1
    assert summary.pass_rate == 0.5
    assert summary.average_steps == 1.5
    assert summary.failed_task_names == ["failing_bug"]
    assert [result.name for result in summary.results] == ["passing_bug", "failing_bug"]


def test_temporary_workspaces_are_removed(tmp_path, monkeypatch):
    created: list[Path] = []
    real_temporary_directory = tempfile.TemporaryDirectory

    class TrackingTemporaryDirectory(real_temporary_directory):
        def __enter__(self):
            path = super().__enter__()
            created.append(Path(path))
            return path

    monkeypatch.setattr(
        benchmark_runner.tempfile,
        "TemporaryDirectory",
        TrackingTemporaryDirectory,
    )
    prompt = "Fix widget.py so the test passes."
    fixture = _make_fixture(tmp_path, "widget_bug", prompt)

    run_benchmark(
        [benchmark_runner.load_benchmark_task(fixture)],
        llm=ScriptedLLM({prompt: [FinalAnswerResponse(final_answer="done")]}),
    )

    assert created
    assert all(not path.exists() for path in created)


def test_shipped_fixtures_start_broken_and_remain_unchanged():
    sample_root = benchmark_runner._sample_repos_root()
    before = _snapshot(sample_root)
    tasks = default_benchmark_tasks(sample_root)
    prompts = {task.prompt: [FinalAnswerResponse(final_answer="done")] for task in tasks}

    summary = run_benchmark(tasks, llm=ScriptedLLM(prompts))

    assert [task.name for task in tasks] == list(BENCHMARK_FIXTURE_NAMES)
    assert summary.total_tasks == len(BENCHMARK_FIXTURE_NAMES)
    assert summary.tasks_passed == 0
    assert summary.pass_rate == 0.0
    assert summary.average_steps == 1.0
    assert summary.failed_task_names == list(BENCHMARK_FIXTURE_NAMES)
    assert all(result.tests_passed is False for result in summary.results)
    assert _snapshot(sample_root) == before


def test_summarize_uses_pytest_success_not_agent_success():
    passed = TaskEvalResult(
        name="fixed",
        agent_result=AgentResult(success=False, error="agent stopped", steps=4),
        tests_passed=True,
        steps=4,
        failure_reason="agent stopped",
        tool_calls=4,
        tool_usage={"read_file": 4},
        tool_failures=1,
        duration_ms=100,
    )
    failed = TaskEvalResult(
        name="still_broken",
        agent_result=AgentResult(success=True, final_answer="done", steps=2),
        tests_passed=False,
        steps=2,
        failure_reason="Fixture tests failed (exit code 1)",
        tool_calls=2,
        tool_usage={"write_file": 2},
        tool_failures=3,
        duration_ms=300,
    )

    summary = summarize([passed, failed])

    assert summary.tasks_passed == 1
    assert summary.pass_rate == 0.5
    assert summary.average_steps == 3.0
    assert summary.failed_task_names == ["still_broken"]
    assert summary.average_tool_calls == 3.0
    assert summary.total_failed_tool_calls == 4
    assert summary.average_duration_ms == 200.0


def test_metrics_observer_counts_requests_and_failed_results():
    observer = BenchmarkMetricsObserver()
    read = ToolCall(tool_name="read_file", arguments={"path": "a.py"})
    missing = ToolCall(tool_name="read_file", arguments={"path": "missing.py"})
    observer.on_event(
        ModelResponseReceived(
            step=1,
            response=FinalAnswerResponse(final_answer="ignored"),
        )
    )
    observer.on_event(ToolCallRequested(step=1, tool_call=read))
    observer.on_event(
        ToolResultReturned(
            step=1,
            tool_call=read,
            result=ToolResult(success=True, output="ok"),
        )
    )
    observer.on_event(ToolCallRequested(step=2, tool_call=missing))
    observer.on_event(
        ToolResultReturned(
            step=2,
            tool_call=missing,
            result=ToolResult(success=False, error="File not found: missing.py"),
        )
    )
    observer.on_event(FinalAnswerReached(step=3, final_answer="done"))

    assert observer.tool_calls == 2
    assert observer.tool_usage == {"read_file": 2}
    assert observer.tool_failures == 1


def test_recorded_metrics_keep_pytest_success_separate(tmp_path):
    prompt = "Fix widget.py so the test passes."
    fixture = _make_fixture(tmp_path, "widget_bug", prompt)
    llm = ScriptedLLM(
        {
            prompt: [
                _read("widget.py"),
                _read("missing.py"),
                _write_fix(),
                FinalAnswerResponse(final_answer="fixed"),
            ]
        }
    )

    result = run_benchmark(
        [benchmark_runner.load_benchmark_task(fixture)],
        llm=llm,
    ).results[0]

    assert result.tests_passed is True
    assert result.tool_calls == 3
    assert result.tool_usage == {"read_file": 2, "write_file": 1}
    assert result.tool_failures == 1
    assert isinstance(result.duration_ms, int)
    assert result.duration_ms >= 0


def test_failed_pytest_with_a_successful_tool_is_not_a_tool_failure(tmp_path):
    prompt = "Fix widget.py so the test passes."
    fixture = _make_fixture(tmp_path, "widget_bug", prompt)
    llm = ScriptedLLM(
        {prompt: [_run_tests(), FinalAnswerResponse(final_answer="still broken")]}
    )

    result = run_benchmark(
        [benchmark_runner.load_benchmark_task(fixture)],
        llm=llm,
    ).results[0]

    assert result.tests_passed is False
    assert result.tool_calls == 1
    assert result.tool_usage == {"run_tests": 1}
    assert result.tool_failures == 0


def test_each_task_gets_a_fresh_metrics_observer(tmp_path):
    first_prompt = "Inspect the first widget."
    second_prompt = "Leave the second widget."
    first = benchmark_runner.load_benchmark_task(
        _make_fixture(tmp_path, "first_bug", first_prompt)
    )
    second = benchmark_runner.load_benchmark_task(
        _make_fixture(tmp_path, "second_bug", second_prompt)
    )
    llm = ScriptedLLM(
        {
            first_prompt: [_list_files(), FinalAnswerResponse(final_answer="seen")],
            second_prompt: [FinalAnswerResponse(final_answer="untouched")],
        }
    )

    summary = run_benchmark([first, second], llm=llm)

    assert summary.results[0].tool_calls == 1
    assert summary.results[0].tool_failures == 0
    assert summary.results[1].tool_calls == 0
    assert summary.results[1].tool_usage == {}
    assert summary.results[1].tool_failures == 0
    assert summary.average_tool_calls == 0.5
    assert summary.total_failed_tool_calls == 0
