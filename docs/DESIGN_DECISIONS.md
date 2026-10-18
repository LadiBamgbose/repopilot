# Design Decisions

Architecture Decision Records (ADRs) for RepoPilot.

---

## DD-001: Introduce a Workspace abstraction

**Status:** Accepted

### Problem

Tools need a repository root to resolve relative paths and enforce workspace
boundaries. Passing `repo_root` into every tool signature couples callers to a
raw path and duplicates resolution logic across tools.

### Alternatives Considered

1. Continue passing `repo_root: str | Path` into each tool.
2. Derive the root from `Path.cwd()` inside every tool.
3. Introduce a shared `Workspace` object that owns the resolved root.

### Decision

Introduce a minimal `Workspace` class that stores a single resolved repository
root as `workspace.root`. Tools accept `workspace: Workspace` instead of a raw
path.

### Rationale

Every RepoPilot tool will operate inside a repository. A small shared
abstraction makes that invariant explicit, centralizes path resolution, and
keeps tool signatures consistent as more tools are added—without committing to
git helpers, indexing, or configuration yet.

---

## DD-002: Separate runtime infrastructure from executable tools

**Status:** Accepted

### Problem

`ToolCall` / `ToolResult` and tool dispatch lived under `tools/`, which mixes
shared runtime contracts with concrete capabilities. That blurs package
boundaries and makes it harder to grow an agent loop on top of tools.

### Alternatives Considered

1. Keep schemas and registry inside `tools/` alongside executables.
2. Place everything under an `agent/` package early.
3. Move protocol and dispatch into a dedicated `core/` package; keep only
   executable tools under `tools/`.

### Decision

- Runtime schemas live in `repopilot.core.tool_protocol`.
- Dispatch lives in `repopilot.core.tool_registry`.
- Executable capabilities remain under `repopilot.tools`.

### Rationale

This establishes a clear execution boundary:

`ToolCall` → `execute_tool` → registry → tool → `ToolResult`

Agent orchestration and LLM logic can later sit above `core/` without treating
schemas or dispatch as tools themselves. The change is structural only; tool
behavior is unchanged.

---

## DD-003: One tool call per agent step

**Status:** Accepted

### Problem

Models can request multiple tool calls in one turn. Parallel or batched
execution complicates conversation state (multiple `call_id`s), error handling,
and observability, and mismatch OpenAI Responses continuation.

### Alternatives Considered

1. Allow parallel tool calls and fan out results in one continue turn.
2. Queue multiple calls inside the runner while the model thinks they ran together.
3. Constrain the loop and API to a single tool call per step.

### Decision

`run_agent` executes exactly one `ToolCall` per step. `OpenAIClient` sets
`parallel_tool_calls=False` so the provider contract matches the runner.

### Rationale

One-tool-per-step keeps the control flow obvious, makes traces linear, and
avoids “No tool output for function call” failures from unmatched call ids.
Efficiency tradeoffs are acceptable for v1 correctness and debuggability.

---

## DD-004: Observer-based instrumentation (no loop coupling)

**Status:** Accepted

### Problem

Benchmarks need metrics and step traces, but baking print/metrics logic into
`run_agent` would couple orchestration to every reporting format.

### Alternatives Considered

1. Hard-code logging inside the agent loop.
2. Return ad hoc dicts from `run_agent` for callers to interpret.
3. Emit typed events to an optional `AgentObserver`.

### Decision

The loop emits `ModelResponseReceived`, `ToolCallRequested`,
`ToolResultReturned`, and `FinalAnswerReached`. Observers (metrics, trace,
console, composite) subscribe without changing tool or model behavior.

### Rationale

Observability stays additive. Unit tests can assert event order; benchmarks can
attach fresh observers per task; production console redaction does not pollute
eval schemas.

---

## DD-005: Deterministic pytest scoring over LLM judging

**Status:** Accepted

### Problem

“Did the agent fix the bug?” must be scored repeatably for a portfolio
benchmark. An LLM judge adds cost, variance, and another failure mode.

### Alternatives Considered

1. Ask a second model whether the diff looks correct.
2. Treat agent final-answer success as the pass bit.
3. Run fixture pytest after each task and use exit code 0 as pass.

### Decision

Harness `score_tests` is the sole source of truth for `tests_passed`. Agent
success, metrics, and traces explain behavior but never override pytest.

### Rationale

Coding tasks already ship tests. Exit codes are cheap, local, and explicit.
Scripted-LLM unit tests can assert scoring without network access.

---

## DD-006: Shared ShopKit fixture with per-task `test_selector`

**Status:** Accepted

### Problem

A multi-module “realistic” repo needs several concurrent defects. Grading the
full pytest suite on every task would make each task fail until every defect is
fixed, which conflates independent skills.

### Alternatives Considered

1. One giant task that must fix everything.
2. Duplicate the whole repo once per defect (drift and maintenance cost).
3. Share one fixture tree; grade each task with a pytest selector.

### Decision

ShopKit tasks reuse `sample_repos/shopkit/` and set `BenchmarkTask.test_selector`
to the relevant test file. Agent `run_tests` still runs the full suite when the
model requests it; only harness scoring is scoped.

### Rationale

Shared layout exercises search/read across packages without turning every run
into an all-or-nothing mega-task. Prompt files under `tasks/` stay out of the
workspace copy so grading text is not leaked as context.
