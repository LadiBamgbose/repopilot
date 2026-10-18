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
    SHOPKIT_TASKS,
    default_benchmark_tasks,
    run_benchmark,
    score_tests,
)
from repopilot.evals.metrics import summarize
from repopilot.evals.metrics_observer import BenchmarkMetricsObserver
from repopilot.evals.schemas import BenchmarkTask, TaskEvalResult
from repopilot.evals.trace_observer import BenchmarkTraceObserver
from repopilot.tools.run_tests import run_tests
from repopilot.workspace import Workspace


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
    expected_names = list(BENCHMARK_FIXTURE_NAMES) + [name for name, _, _ in SHOPKIT_TASKS]
    prompts = {task.prompt: [FinalAnswerResponse(final_answer="done")] for task in tasks}

    summary = run_benchmark(tasks, llm=ScriptedLLM(prompts))

    assert [task.name for task in tasks] == expected_names
    assert summary.total_tasks == len(expected_names)
    assert summary.tasks_passed == 0
    assert summary.pass_rate == 0.0
    assert summary.average_steps == 1.0
    assert summary.failed_task_names == expected_names
    assert all(result.tests_passed is False for result in summary.results)
    assert _snapshot(sample_root) == before


def _make_shared_fixture(root: Path) -> Path:
    fixture = root / "shared_shop"
    (fixture / "tests").mkdir(parents=True)
    (fixture / "tasks").mkdir()
    (fixture / "alpha.py").write_text("def alpha() -> int:\n    return 1\n", encoding="utf-8")
    (fixture / "beta.py").write_text("def beta() -> int:\n    return 1\n", encoding="utf-8")
    (fixture / "tests" / "test_alpha.py").write_text(
        "from alpha import alpha\n\n\ndef test_alpha():\n    assert alpha() == 2\n",
        encoding="utf-8",
    )
    (fixture / "tests" / "test_beta.py").write_text(
        "from beta import beta\n\n\ndef test_beta():\n    assert beta() == 2\n",
        encoding="utf-8",
    )
    (fixture / "pytest.ini").write_text(
        "[pytest]\ntestpaths = tests\npythonpath = .\n",
        encoding="utf-8",
    )
    (fixture / "tasks" / "alpha.txt").write_text("Fix alpha.\n", encoding="utf-8")
    (fixture / "tasks" / "beta.txt").write_text("Fix beta.\n", encoding="utf-8")
    return fixture


def test_multiple_tasks_can_share_one_fixture_dir(tmp_path):
    fixture = _make_shared_fixture(tmp_path)
    alpha = BenchmarkTask(
        name="alpha_task",
        fixture_dir=fixture,
        prompt="Fix alpha.",
        test_selector="tests/test_alpha.py",
    )
    beta = BenchmarkTask(
        name="beta_task",
        fixture_dir=fixture,
        prompt="Fix beta.",
        test_selector="tests/test_beta.py",
    )

    assert alpha.fixture_dir == beta.fixture_dir
    assert alpha.test_selector != beta.test_selector


def test_task_selector_scores_only_selected_tests(tmp_path):
    fixture = _make_shared_fixture(tmp_path)
    before = _snapshot(fixture)
    alpha_prompt = "Fix alpha."
    beta_prompt = "Fix beta."
    alpha = BenchmarkTask(
        name="alpha_task",
        fixture_dir=fixture,
        prompt=alpha_prompt,
        test_selector="tests/test_alpha.py",
    )
    beta = BenchmarkTask(
        name="beta_task",
        fixture_dir=fixture,
        prompt=beta_prompt,
        test_selector="tests/test_beta.py",
    )
    llm = ScriptedLLM(
        {
            alpha_prompt: [
                ToolCallResponse(
                    tool_call=ToolCall(
                        tool_name="write_file",
                        arguments={
                            "path": "alpha.py",
                            "contents": "def alpha() -> int:\n    return 2\n",
                        },
                    )
                ),
                FinalAnswerResponse(final_answer="alpha fixed"),
            ],
            beta_prompt: [FinalAnswerResponse(final_answer="left alone")],
        }
    )

    summary = run_benchmark([alpha, beta], llm=llm)

    assert summary.results[0].tests_passed is True
    assert summary.results[1].tests_passed is False
    assert summary.tasks_passed == 1
    assert (fixture / "alpha.py").read_text(encoding="utf-8") == "def alpha() -> int:\n    return 1\n"
    assert _snapshot(fixture) == before


def test_selected_task_can_pass_while_unrelated_tests_still_fail(tmp_path):
    fixture = _make_shared_fixture(tmp_path)
    prompt = "Fix alpha only."
    task = BenchmarkTask(
        name="alpha_task",
        fixture_dir=fixture,
        prompt=prompt,
        test_selector="tests/test_alpha.py",
    )
    llm = ScriptedLLM(
        {
            prompt: [
                ToolCallResponse(
                    tool_call=ToolCall(
                        tool_name="write_file",
                        arguments={
                            "path": "alpha.py",
                            "contents": "def alpha() -> int:\n    return 2\n",
                        },
                    )
                ),
                FinalAnswerResponse(final_answer="done"),
            ]
        }
    )

    result = run_benchmark([task], llm=llm).results[0]
    assert result.tests_passed is True

    # Full-suite scoring on a copy that only fixed alpha still fails.
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace_dir = Path(temp_dir) / "workspace"
        benchmark_runner._copy_fixture(fixture, workspace_dir)
        (workspace_dir / "alpha.py").write_text(
            "def alpha() -> int:\n    return 2\n",
            encoding="utf-8",
        )
        workspace = Workspace(workspace_dir)
        full = score_tests(workspace=workspace, test_selector=None)
        selected = score_tests(
            workspace=workspace,
            test_selector="tests/test_alpha.py",
        )
        agent_view = run_tests(workspace=workspace)

    assert full.output["exit_code"] != 0
    assert selected.output["exit_code"] == 0
    assert agent_view.output["exit_code"] != 0


def test_tasks_directory_is_not_copied_into_workspace(tmp_path):
    fixture = _make_shared_fixture(tmp_path)
    prompt = "Inspect files."
    task = BenchmarkTask(
        name="alpha_task",
        fixture_dir=fixture,
        prompt=prompt,
        test_selector="tests/test_alpha.py",
    )
    llm = ScriptedLLM({prompt: [_list_files(), FinalAnswerResponse(final_answer="done")]})

    run_benchmark([task], llm=llm)

    listed = llm.tool_results[0].output
    assert "tasks/alpha.txt" not in listed
    assert "alpha.py" in listed


def test_no_selector_still_scores_full_suite(tmp_path):
    prompt = "Fix widget.py so the test passes."
    fixture = _make_fixture(tmp_path, "widget_bug", prompt)
    task = benchmark_runner.load_benchmark_task(fixture)
    assert task.test_selector is None

    failing = run_benchmark(
        [task],
        llm=ScriptedLLM({prompt: [FinalAnswerResponse(final_answer="nope")]}),
    ).results[0]
    assert failing.tests_passed is False

    passing = run_benchmark(
        [task],
        llm=ScriptedLLM(
            {
                prompt: [
                    _write_fix(),
                    FinalAnswerResponse(final_answer="fixed"),
                ]
            }
        ),
    ).results[0]
    assert passing.tests_passed is True


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


def test_trace_observer_records_tool_calls_and_results_in_order():
    observer = BenchmarkTraceObserver()
    write = ToolCall(
        tool_name="write_file",
        arguments={"path": "widget.py", "contents": FIXED_SOURCE},
    )
    tests = ToolCall(tool_name="run_tests", arguments={})

    observer.on_event(
        ModelResponseReceived(step=1, response=_write_fix())
    )
    observer.on_event(ToolCallRequested(step=1, tool_call=write))
    observer.on_event(
        ToolResultReturned(
            step=1,
            tool_call=write,
            result=ToolResult(success=True, output="wrote widget.py"),
        )
    )
    observer.on_event(
        ModelResponseReceived(step=2, response=_run_tests())
    )
    observer.on_event(ToolCallRequested(step=2, tool_call=tests))
    observer.on_event(
        ToolResultReturned(
            step=2,
            tool_call=tests,
            result=ToolResult(
                success=True,
                output={
                    "exit_code": 1,
                    "stdout": (
                        "===== short test summary info =====\n"
                        "FAILED test_widget.py::test_value - assert 1 == 2\n"
                    ),
                },
            ),
        )
    )
    observer.on_event(FinalAnswerReached(step=3, final_answer="still broken"))

    assert [event.event_type for event in observer.events] == [
        "model_response",
        "tool_call",
        "tool_result",
        "model_response",
        "tool_call",
        "tool_result",
        "final_answer",
    ]
    assert [event.step for event in observer.events] == [1, 1, 1, 2, 2, 2, 3]
    write_call = observer.events[1]
    assert write_call.tool_name == "write_file"
    assert write_call.path == "widget.py"
    write_result = observer.events[2]
    assert write_result.path == "widget.py"
    assert write_result.tool_success is True
    run_result = observer.events[5]
    assert run_result.tool_name == "run_tests"
    assert run_result.exit_code == 1
    assert run_result.failure_summary is not None
    assert "FAILED test_widget.py::test_value" in run_result.failure_summary
    assert observer.events[6].final_answer == "still broken"


def test_write_file_trace_includes_target_path():
    observer = BenchmarkTraceObserver()
    tool_call = ToolCall(
        tool_name="write_file",
        arguments={"path": "src/quote.py", "contents": "x = 1\n"},
    )
    observer.on_event(ToolCallRequested(step=1, tool_call=tool_call))
    observer.on_event(
        ToolResultReturned(
            step=1,
            tool_call=tool_call,
            result=ToolResult(success=True, output="ok"),
        )
    )

    assert observer.events[0].path == "src/quote.py"
    assert observer.events[1].path == "src/quote.py"
    assert observer.events[0].tool_arguments is not None
    assert observer.events[0].tool_arguments["path"] == "src/quote.py"


def test_run_tests_trace_includes_exit_code_and_failure_summary():
    observer = BenchmarkTraceObserver()
    tool_call = ToolCall(tool_name="run_tests", arguments={})
    observer.on_event(ToolCallRequested(step=2, tool_call=tool_call))
    observer.on_event(
        ToolResultReturned(
            step=2,
            tool_call=tool_call,
            result=ToolResult(
                success=True,
                output={
                    "exit_code": 1,
                    "stdout": (
                        "FAILED tests/test_quote.py::test_express - AssertionError\n"
                        "FAILED tests/test_quote.py::test_bulk - assert False\n"
                    ),
                },
            ),
        )
    )

    result = observer.events[1]
    assert result.exit_code == 1
    assert result.failure_summary is not None
    assert "test_express" in result.failure_summary
    assert "test_bulk" in result.failure_summary
    assert result.tool_success is True


def test_benchmark_traces_do_not_leak_between_tasks(tmp_path):
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

    first_trace = summary.results[0].trace
    second_trace = summary.results[1].trace
    assert any(event.event_type == "tool_call" for event in first_trace)
    assert any(
        event.tool_name == "list_files" for event in first_trace if event.tool_name
    )
    assert not any(event.event_type == "tool_call" for event in second_trace)
    assert any(event.event_type == "final_answer" for event in second_trace)


def test_recorded_traces_keep_pytest_success_separate(tmp_path):
    prompt = "Fix widget.py so the test passes."
    fixture = _make_fixture(tmp_path, "widget_bug", prompt)
    llm = ScriptedLLM(
        {
            prompt: [
                _read("widget.py"),
                _write_fix(),
                _run_tests(),
                FinalAnswerResponse(final_answer="fixed"),
            ]
        }
    )

    result = run_benchmark(
        [benchmark_runner.load_benchmark_task(fixture)],
        llm=llm,
    ).results[0]

    assert result.tests_passed is True
    assert result.failure_reason is None
    assert any(event.path == "widget.py" for event in result.trace)
    run_results = [
        event
        for event in result.trace
        if event.event_type == "tool_result" and event.tool_name == "run_tests"
    ]
    assert len(run_results) == 1
    assert run_results[0].exit_code == 0
    assert run_results[0].failure_summary is None


def test_failed_pytest_trace_still_uses_harness_pass_fail(tmp_path):
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
    assert result.failure_reason is not None
    run_results = [
        event
        for event in result.trace
        if event.event_type == "tool_result" and event.tool_name == "run_tests"
    ]
    assert len(run_results) == 1
    assert run_results[0].exit_code == 1
    assert run_results[0].failure_summary is not None
    assert "FAILED" in run_results[0].failure_summary
