# RepoPilot Roadmap

## v1.0 — complete

Core local coding agent, tools, observability, and deterministic evaluation are implemented and documented.

### Runtime and tools

- [x] Workspace abstraction (`workspace.root`) with path-boundary checks
- [x] Shared tool protocol (`ToolCall`, `ToolResult`)
- [x] Tool registry and `execute_tool` dispatch
- [x] Tools: `list_files`, `read_file`, `write_file`, `search_repo`, `run_tests`
- [x] Provider-neutral `ToolDefinition` / JSON schemas

### Agent and LLM

- [x] `LLMClient` protocol and scripted test doubles
- [x] OpenAI Responses API client (`previous_response_id`, function `call_id`)
- [x] One-tool-per-step agent loop with max-step limit
- [x] Tool failures returned as observations (no silent swallow)

### Observability

- [x] Typed agent events + `AgentObserver` protocol
- [x] Console, metrics, and bounded benchmark trace observers
- [x] Composite fan-out for simultaneous metrics + traces

### Evaluation

- [x] `BenchmarkTask` / `TaskEvalResult` / `EvalSummary` schemas
- [x] Temp-copy fixture isolation and reset
- [x] Pytest exit code as sole pass/fail criterion
- [x] 13 mini-repo tasks + 5 ShopKit shared-repo tasks with `test_selector`
- [x] CLI metrics output and optional `--trace <task>`

v1 deliberately stops here: no new agent features are required for a readable portfolio baseline.

---

## Future work (not started)

These ideas are explicitly **out of scope** for v1. Do not treat them as missing bugs in the current release.

### GitHub issue / branch / PR workflow

- Ingest a GitHub issue as the task source
- Create a working branch, commit agent edits, open a PR-style report
- Wire authentication and repo selection for remote targets

### Richer context management

- Smarter file selection over larger repositories
- Summaries / indexes so the model does not rely only on search + read loops
- Explicit context budgets and truncation policy

### Persistence

- Store run history, metrics, and traces beyond a single process
- Compare regression runs over time
- Optional artifact export for failed tasks

### Self-hosted open-source model inference (vLLM)

- Run open models behind the same `LLMClient` boundary
- Keep tools and the agent loop provider-neutral
- Document hardware and latency tradeoffs versus hosted APIs

### Advanced planning and reflection

- Structured multi-step plans before edits
- Explicit reflection / retry policies after test failure
- Separate planner vs editor roles if evidence shows they help

### Platform / production (longer horizon)

- API job queue and multi-tenant isolation
- Cost and token accounting
- CI gates for lint plus benchmark smoke runs
- Hardened sandboxing beyond path checks
