"""Run benchmark fixtures in temporary workspaces."""

import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from repopilot.agent.observer import CompositeAgentObserver
from repopilot.agent.runner import MAX_STEPS, run_agent
from repopilot.agent.schemas import AgentResult
from repopilot.core.tool_protocol import ToolResult
from repopilot.evals.metrics import summarize
from repopilot.evals.metrics_observer import BenchmarkMetricsObserver
from repopilot.evals.schemas import BenchmarkTask, EvalSummary, TaskEvalResult
from repopilot.evals.trace_observer import BenchmarkTraceObserver, TraceEvent
from repopilot.llm.client import LLMClient
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
    "email_normalize",
    "status_label",
    "tax_invoice",
    "password_rules",
    "payment_timeout",
)

SHOPKIT_TASKS = (
    (
        "loyalty_discount",
        "tests/test_loyalty_discount.py",
        "tasks/loyalty_discount.txt",
    ),
    (
        "payment_timeout_config",
        "tests/test_payment_timeout.py",
        "tasks/payment_timeout.txt",
    ),
    (
        "shipping_surcharge",
        "tests/test_shipping_surcharge.py",
        "tasks/shipping_surcharge.txt",
    ),
    (
        "coupon_stacking",
        "tests/test_coupon_stacking.py",
        "tasks/coupon_stacking.txt",
    ),
    (
        "order_export",
        "tests/test_order_export.py",
        "tasks/order_export.txt",
    ),
)

_COPY_SKIP = frozenset(
    {".git", ".pytest_cache", "__pycache__", ".venv", "task.txt", "tasks"}
)


def default_benchmark_tasks(sample_root: Path | None = None) -> list[BenchmarkTask]:
    """Load the explicit benchmark list from sample_repos."""
    root = _sample_repos_root() if sample_root is None else sample_root
    tasks = [load_benchmark_task(root / name) for name in BENCHMARK_FIXTURE_NAMES]
    tasks.extend(load_shopkit_tasks(root / "shopkit"))
    return tasks


def load_benchmark_task(fixture_dir: Path) -> BenchmarkTask:
    """Read one fixture's task prompt. The prompt file stays out of the workspace."""
    prompt = (fixture_dir / "task.txt").read_text(encoding="utf-8").strip()
    return BenchmarkTask(
        name=fixture_dir.name,
        fixture_dir=fixture_dir,
        prompt=prompt,
    )


def load_shopkit_tasks(shopkit_root: Path) -> list[BenchmarkTask]:
    """Load the shared ShopKit tasks that reuse one fixture directory."""
    tasks: list[BenchmarkTask] = []
    for name, test_selector, prompt_file in SHOPKIT_TASKS:
        prompt = (shopkit_root / prompt_file).read_text(encoding="utf-8").strip()
        tasks.append(
            BenchmarkTask(
                name=name,
                fixture_dir=shopkit_root,
                prompt=prompt,
                test_selector=test_selector,
            )
        )
    return tasks


def run_benchmark(
    tasks: list[BenchmarkTask],
    *,
    llm: LLMClient,
    max_steps: int = MAX_STEPS,
) -> EvalSummary:
    """Evaluate each task in a fresh copy, then delete that copy.

    Benchmark success is pytest exit code 0 for the task's score tests. The
    source fixture is never used as the agent workspace. The agent's own
    ``run_tests`` tool still runs the full suite when the model calls it.
    """
    results: list[TaskEvalResult] = []
    for task in tasks:
        with tempfile.TemporaryDirectory(prefix=f"repopilot-{task.name}-") as temp_dir:
            workspace_dir = Path(temp_dir) / "workspace"
            _copy_fixture(task.fixture_dir, workspace_dir)
            workspace = Workspace(workspace_dir)
            metrics = BenchmarkMetricsObserver()
            tracer = BenchmarkTraceObserver()
            observer = CompositeAgentObserver([metrics, tracer])
            started = time.perf_counter()
            agent_result = run_agent(
                task.prompt,
                llm=llm,
                workspace=workspace,
                max_steps=max_steps,
                observer=observer,
            )
            duration_ms = int((time.perf_counter() - started) * 1000)
            test_result = score_tests(
                workspace=workspace,
                test_selector=task.test_selector,
            )
        results.append(
            _task_result(
                task.name,
                agent_result,
                test_result,
                tool_calls=metrics.tool_calls,
                tool_usage=dict(metrics.tool_usage),
                tool_failures=metrics.tool_failures,
                duration_ms=duration_ms,
                trace=list(tracer.events),
            )
        )
    return summarize(results)


def score_tests(
    *,
    workspace: Workspace,
    test_selector: str | None = None,
) -> ToolResult:
    """Run pytest for harness scoring only.

    When ``test_selector`` is set, only that path is collected. This does not
    change the agent-facing ``run_tests`` tool, which always runs the full suite.
    """
    command = [sys.executable, "-m", "pytest"]
    if test_selector is not None:
        command.append(test_selector)
    started = time.perf_counter()

    try:
        completed = subprocess.run(
            command,
            cwd=workspace.root,
            capture_output=True,
            text=True,
            shell=False,
        )
    except OSError as exc:
        duration_ms = int((time.perf_counter() - started) * 1000)
        return ToolResult(
            success=False,
            error=f"Failed to run tests: {exc}",
            duration_ms=duration_ms,
        )

    duration_ms = int((time.perf_counter() - started) * 1000)
    return ToolResult(
        success=True,
        output={
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        },
        duration_ms=duration_ms,
    )


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
    trace: list[TraceEvent],
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
        trace=trace,
    )


def _pytest_outcome(test_result: ToolResult) -> tuple[bool, str | None]:
    if not test_result.success:
        return False, test_result.error or "Failed to run fixture tests"
    output = test_result.output if isinstance(test_result.output, dict) else {}
    exit_code = output.get("exit_code")
    if exit_code == 0:
        return True, None
    return False, f"Fixture tests failed (exit code {exit_code})"
