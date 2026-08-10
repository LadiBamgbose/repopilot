# RepoPilot Roadmap

Long-term plan for building RepoPilot into a transparent, testable AI coding agent.

## Phase 1: Core Runtime

Foundation for safe, testable tool execution inside a repository workspace.

- [ ] Workspace abstraction (`workspace.root`)
- [ ] Shared tool protocol (`ToolCall`, `ToolResult`)
- [ ] Tool registry and `execute_tool` dispatch
- [ ] `read_file` tool with repository-boundary checks
- [ ] Unit tests for `read_file` and tool dispatch
- [ ] Additional repository tools (`write_file`, `edit_file`, `search_repo`, git helpers, `run_tests`)
- [ ] Structured event logging for tool invocations
- [ ] Configuration loading for workspace and runtime settings

## Phase 2: Coding Agent

Orchestrate multi-step work from a GitHub issue to a validated code change.

- [ ] LLM client abstraction
- [ ] Planning prompts and structured plan schema
- [ ] Context selection over the local repository
- [ ] Agent loop that issues `ToolCall`s through `execute_tool`
- [ ] Edit / patch application workflow
- [ ] Test-driven retry after failure
- [ ] PR-style final report generation

## Phase 3: Evaluation Framework

Measure agent quality with repeatable benchmarks.

- [ ] Benchmark task format and fixtures
- [ ] Benchmark runner over sample repositories
- [ ] Success / failure scoring criteria
- [ ] Cost and latency tracking per run
- [ ] Regression suite for core agent behaviors

## Phase 4: Inference Platform

Operate the agent as a service rather than a local script.

- [ ] API surface for submitting issues / tasks
- [ ] Job queue and run lifecycle
- [ ] Model routing and pricing integration
- [ ] Persistent run history and artifacts
- [ ] Authentication and multi-tenant workspace isolation

## Phase 5: Production Readiness

Harden RepoPilot for reliable, observable operation.

- [ ] Robust error handling and timeout policies
- [ ] Observability (metrics, traces, structured logs)
- [ ] Security review of tool sandboxing and path controls
- [ ] CI gates for tests, lint, and benchmark smoke runs
- [ ] Operational runbooks and release process
