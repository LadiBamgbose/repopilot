"""Collect tool-call metrics from agent events."""

from repopilot.agent.observer import AgentEvent, ToolCallRequested, ToolResultReturned


class BenchmarkMetricsObserver:
    """Count tool requests and failed executions for one benchmark task."""

    def __init__(self) -> None:
        self.tool_calls = 0
        self.tool_usage: dict[str, int] = {}
        self.tool_failures = 0

    def on_event(self, event: AgentEvent) -> None:
        if isinstance(event, ToolCallRequested):
            name = event.tool_call.tool_name
            self.tool_calls += 1
            self.tool_usage[name] = self.tool_usage.get(name, 0) + 1
        elif isinstance(event, ToolResultReturned) and not event.result.success:
            self.tool_failures += 1
