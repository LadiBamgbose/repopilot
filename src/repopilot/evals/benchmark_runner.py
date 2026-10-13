"""Run benchmark fixtures in temporary workspaces."""

import shutil
import tempfile
import time
from pathlib import Path

from repopilot.agent.runner import MAX_STEPS, run_agent
from repopilot.agent.schemas import AgentResult
from repopilot.core.tool_protocol import ToolResult
from repopilot.evals.metrics import summarize
from repopilot.evals.metrics_observer import BenchmarkMetricsObserver
from repopilot.evals.schemas import BenchmarkTask, EvalSummary, TaskEvalResult
from repopilot.llm.client import LLMClient
from repopilot.tools.run_tests import run_tests
from repopilot.workspace import Workspace

BENCHMARK_FIXTURE_NAMES = (
    "calculator_bug",
    "case_bug",
    "off_by_one_bug",
    "greet_bug",
    "invoice_fee",
    "shipping_quote",
    "order_total",
    "member_greeting",
)

_COPY_SKIP = frozenset({".git", ".pytest_cache", "__pycache__", ".venv", "task.txt"})


def default_benchmark_tasks(sample_root: Path | None = None) -> list[BenchmarkTask]:
    """Load the explicit benchmark list from sample_repos."""
    root = _sample_repos_root() if sample_root is None else sample_root
    return [load_benchmark_task(root / name) for name in BENCHMARK_FIXTURE_NAMES]


def load_benchmark_task(fixture_dir: Path) -> BenchmarkTask:
    """Read one fixture's task prompt. The prompt file stays out of the workspace."""
    prompt = (fixture_dir / "task.txt").read_text(encoding="utf-8").strip()
    return BenchmarkTask(
        name=fixture_dir.name,
        fixture_dir=fixture_dir,
        prompt=prompt,
    )


def run_benchmark(
    tasks: list[BenchmarkTask],
    *,
    llm: LLMClient,
    max_steps: int = MAX_STEPS,
) -> EvalSummary:
    """Evaluate each task in a fresh copy, then delete that copy.

    Benchmark success is pytest exit code 0 in the copy. The source fixture
    is never used as the agent workspace.
    """
    results: list[TaskEvalResult] = []
    for task in tasks:
        with tempfile.TemporaryDirectory(prefix=f"repopilot-{task.name}-") as temp_dir:
            workspace_dir = Path(temp_dir) / "workspace"
            _copy_fixture(task.fixture_dir, workspace_dir)
            workspace = Workspace(workspace_dir)
            observer = BenchmarkMetricsObserver()
            started = time.perf_counter()
            agent_result = run_agent(
                task.prompt,
                llm=llm,
                workspace=workspace,
                max_steps=max_steps,
                observer=observer,
            )
            duration_ms = int((time.perf_counter() - started) * 1000)
            test_result = run_tests(workspace=workspace)
        results.append(
            _task_result(
                task.name,
                agent_result,
                test_result,
                tool_calls=observer.tool_calls,
                tool_usage=dict(observer.tool_usage),
                tool_failures=observer.tool_failures,
                duration_ms=duration_ms,
            )
        )
    return summarize(results)


def _sample_repos_root() -> Path:
    return Path(__file__).resolve().parents[3] / "sample_repos"


def _copy_fixture(source: Path, destination: Path) -> None:
    shutil.copytree(source, destination, ignore=_ignore_fixture_files)


def _ignore_fixture_files(_directory: str, names: list[str]) -> set[str]:
    return {name for name in names if name in _COPY_SKIP}


def _task_result(
    name: str,
    agent_result: AgentResult,
    test_result: ToolResult,
    *,
    tool_calls: int,
    tool_usage: dict[str, int],
    tool_failures: int,
    duration_ms: int,
) -> TaskEvalResult:
    tests_passed, test_failure = _pytest_outcome(test_result)
    if not agent_result.success:
        failure_reason = agent_result.error or "Agent run failed"
    elif not tests_passed:
        failure_reason = test_failure
    else:
        failure_reason = None
    return TaskEvalResult(
        name=name,
        agent_result=agent_result,
        tests_passed=tests_passed,
        steps=agent_result.steps,
        failure_reason=failure_reason,
        tool_calls=tool_calls,
        tool_usage=tool_usage,
        tool_failures=tool_failures,
        duration_ms=duration_ms,
    )


def _pytest_outcome(test_result: ToolResult) -> tuple[bool, str | None]:
    if not test_result.success:
        return False, test_result.error or "Failed to run fixture tests"
    output = test_result.output if isinstance(test_result.output, dict) else {}
    exit_code = output.get("exit_code")
    if exit_code == 0:
        return True, None
    return False, f"Fixture tests failed (exit code {exit_code})"
