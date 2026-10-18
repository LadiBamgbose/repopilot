"""Deterministic benchmark evaluation."""

from repopilot.evals.benchmark_runner import (
    BENCHMARK_FIXTURE_NAMES,
    SHOPKIT_TASKS,
    default_benchmark_tasks,
    run_benchmark,
    score_tests,
)
from repopilot.evals.schemas import BenchmarkTask, EvalSummary, TaskEvalResult
from repopilot.evals.trace_observer import BenchmarkTraceObserver, TraceEvent, format_trace

__all__ = [
    "BENCHMARK_FIXTURE_NAMES",
    "SHOPKIT_TASKS",
    "BenchmarkTask",
    "BenchmarkTraceObserver",
    "EvalSummary",
    "TaskEvalResult",
    "TraceEvent",
    "default_benchmark_tasks",
    "format_trace",
    "run_benchmark",
    "score_tests",
]
