"""Schemas for deterministic benchmark evaluation."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from repopilot.agent.schemas import AgentResult
from repopilot.evals.trace_observer import TraceEvent


class BenchmarkTask(BaseModel):
    """One controlled coding task loaded from a fixture directory."""

    model_config = ConfigDict(extra="forbid")

    name: str
    fixture_dir: Path
    prompt: str
    test_selector: str | None = None


class TaskEvalResult(BaseModel):
    """Outcome of one benchmark task."""

    model_config = ConfigDict(extra="forbid")

    name: str
    agent_result: AgentResult
    tests_passed: bool
    steps: int
    failure_reason: str | None = None
    tool_calls: int
    tool_usage: dict[str, int]
    tool_failures: int
    duration_ms: int
    trace: list[TraceEvent] = Field(default_factory=list)


class EvalSummary(BaseModel):
    """Aggregate result for one benchmark run."""

    model_config = ConfigDict(extra="forbid")

    total_tasks: int
    tasks_passed: int
    pass_rate: float
    average_steps: float
    failed_task_names: list[str]
    average_tool_calls: float
    total_failed_tool_calls: int
    average_duration_ms: float
    results: list[TaskEvalResult]
