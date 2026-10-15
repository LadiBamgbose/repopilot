"""Run the benchmark fixtures with the real OpenAI API.

Run from the repository root:

    PYTHONPATH=src python scripts/run_benchmark.py

The API key is read by the OpenAI SDK from OPENAI_API_KEY.
Override the model with OPENAI_MODEL.
"""

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from repopilot.evals.benchmark_runner import default_benchmark_tasks, run_benchmark
from repopilot.llm.openai_client import OpenAIClient

MODEL = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")


def main() -> None:
    summary = run_benchmark(default_benchmark_tasks(), llm=OpenAIClient(model=MODEL))
    for result in summary.results:
        print(
            f"{result.name}: tests_passed={result.tests_passed} "
            f"steps={result.steps} tool_calls={result.tool_calls} "
            f"tool_usage={result.tool_usage} tool_failures={result.tool_failures} "
            f"duration_ms={result.duration_ms} failure_reason={result.failure_reason}"
        )
    print(f"total tasks: {summary.total_tasks}")
    print(f"tasks passed: {summary.tasks_passed}")
    print(f"pass rate: {summary.pass_rate}")
    print(f"average steps: {summary.average_steps}")
    print(f"average tool calls: {summary.average_tool_calls}")
    print(f"total failed tool calls: {summary.total_failed_tool_calls}")
    print(f"average duration ms: {summary.average_duration_ms}")
    print(f"failed task names: {summary.failed_task_names}")


if __name__ == "__main__":
    main()
