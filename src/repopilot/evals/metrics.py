"""Aggregate benchmark task results."""

from repopilot.evals.schemas import EvalSummary, TaskEvalResult


def summarize(results: list[TaskEvalResult]) -> EvalSummary:
    """Build pass rate, average steps, and failed task names."""
    total_tasks = len(results)
    tasks_passed = sum(1 for result in results if result.tests_passed)
    if total_tasks == 0:
        pass_rate = 0.0
        average_steps = 0.0
        average_tool_calls = 0.0
        average_duration_ms = 0.0
    else:
        pass_rate = tasks_passed / total_tasks
        average_steps = sum(result.steps for result in results) / total_tasks
        average_tool_calls = sum(result.tool_calls for result in results) / total_tasks
        average_duration_ms = sum(result.duration_ms for result in results) / total_tasks
    failed_task_names = [
        result.name for result in results if not result.tests_passed
    ]
    return EvalSummary(
        total_tasks=total_tasks,
        tasks_passed=tasks_passed,
        pass_rate=pass_rate,
        average_steps=average_steps,
        failed_task_names=failed_task_names,
        average_tool_calls=average_tool_calls,
        total_failed_tool_calls=sum(result.tool_failures for result in results),
        average_duration_ms=average_duration_ms,
        results=results,
    )
