"""Schemas for deterministic benchmark evaluation."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from repopilot.agent.schemas import AgentResult


class BenchmarkTask(BaseModel):
    """One controlled coding task loaded from a fixture directory."""

    model_config = ConfigDict(extra="forbid")

    name: str
    fixture_dir: Path
    prompt: str


class TaskEvalResult(BaseModel):
    """Outcome of one benchmark task."""

    model_config = ConfigDict(extra="forbid")

    name: str
    agent_result: AgentResult
    tests_passed: bool
    steps: int
    failure_reason: str | None = None


class EvalSummary(BaseModel):
    """Aggregate result for one benchmark run."""

    model_config = ConfigDict(extra="forbid")

    total_tasks: int
    tasks_passed: int
    pass_rate: float
    average_steps: float
    failed_task_names: list[str]
    results: list[TaskEvalResult]
