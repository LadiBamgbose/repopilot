# RepoPilot

RepoPilot is a local AI coding agent that fixes small repository bugs with tool use, pytest validation, and measurable evaluation.

It is an Applied AI Engineering portfolio project: transparent orchestration, provider-neutral tools, workspace safety, observer-based instrumentation, and a deterministic benchmark harness.

## Problem

LLM demos often claim “the agent fixed the code” without a durable way to prove it. RepoPilot treats coding-agent work as an engineering system:

- the model proposes one tool call at a time
- tools mutate or inspect only a bounded workspace
- pytest decides whether the fix worked
- metrics and step traces explain cost and behavior when runs succeed or fail

## Architecture overview

```
Task prompt
    │
    ▼
run_agent (decision loop)
    │
    ├── LLMClient (OpenAI Responses API today)
    │       returns FinalAnswerResponse | ToolCallResponse
    │
    ├── execute_tool → TOOL_REGISTRY → workspace tools
    │
    └── AgentObserver events (optional)
            ├── BenchmarkMetricsObserver
            └── BenchmarkTraceObserver
                    │
                    ▼
            TaskEvalResult → EvalSummary
            (pytest exit code is pass/fail)
```

| Layer | Role |
|-------|------|
| `agent/` | Loop, response schemas, observers |
| `llm/` | Provider client (`LLMClient` protocol + `OpenAIClient`) |
| `core/` | `ToolCall` / `ToolResult`, registry, provider-neutral tool schemas |
| `tools/` | Executable capabilities (`list_files`, `read_file`, …) |
| `workspace/` | Resolved repo root + path boundary checks |
| `evals/` | Benchmark fixtures, scoring, metrics, traces |

## Agent loop

`run_agent` alternates model decisions and tool execution:

1. `llm.start(task)` returns a tool call or final answer.
2. Each step emits `ModelResponseReceived`.
3. On a tool call: emit `ToolCallRequested`, run `execute_tool`, emit `ToolResultReturned`, then `llm.continue_with_tool_result(...)`.
4. On a final answer: emit `FinalAnswerReached` and return `AgentResult`.
5. Stop after `MAX_STEPS` (20) if there is still no final answer.

The loop does not invent retries or planning policy beyond what the model chooses. Tool failures are returned as `ToolResult` observations.

## Available tools

| Tool | Purpose |
|------|---------|
| `list_files` | Recursively list files under the workspace root |
| `read_file` | Read a UTF-8 text file |
| `write_file` | Overwrite an existing UTF-8 text file |
| `search_repo` | Substring search across UTF-8 files |
| `run_tests` | Run the workspace pytest suite |

## Provider-neutral tool schema design

Tools are registered as `ToolDefinition` values: name, description, callable, and a Pydantic `args_model`.

- Runtime contracts (`ToolCall`, `ToolResult`) live in `core/` and are independent of any vendor SDK.
- `tool_schema()` exposes JSON-schema parameters for any provider adapter.
- OpenAI-specific formatting lives only in `llm/openai_tools.py` (`to_openai_function_tools`).

Swapping providers should mean a new client adapter, not rewriting tools.

## OpenAI Responses API integration

`OpenAIClient` uses the Responses API for one active agent run:

- conversation continuity via `previous_response_id`
- tool observations tied to the pending function `call_id`
- `parallel_tool_calls=False` so the runner’s one-tool-per-step contract matches the API

Default model: `gpt-4.1-mini` (override with `OPENAI_MODEL`). Auth: `OPENAI_API_KEY`.

## Workspace safety boundary

Tools receive a `Workspace` with a single resolved root. File paths are resolved under that root; attempts to escape the workspace fail. Benchmarks copy fixtures into temporary directories so source fixtures stay untouched.

## Observability architecture

Instrumentation is event-driven. The agent loop emits typed events; observers never change tool or model behavior.

- `ConsoleAgentObserver` — short, redacted console traces
- `BenchmarkMetricsObserver` — tool call counts, usage by name, tool failures, used for aggregate metrics
- `BenchmarkTraceObserver` — bounded step-level traces (args, paths, pytest exit codes / failure summaries)
- `CompositeAgentObserver` — fan-out to several observers per task

## Deterministic evaluation

Pass/fail is **pytest exit code 0**, not an LLM judge and not “the agent said it worked.”

Each task runs in a fresh temp copy of its fixture. Aggregate metrics (steps, tool calls, failures, duration) stay separate from the pass bit. Optional `--trace <task>` prints a detailed execution path without dumping every successful run.

See [docs/EVALUATION.md](docs/EVALUATION.md) for schemas, ShopKit `test_selector` grading, and limitations.

## Current benchmark structure

**18 tasks total**

1. **13 focused mini-repos** under `sample_repos/` (one bug / one suite each), e.g. `calculator_bug`, `shipping_quote`, `password_rules`.
2. **5 ShopKit tasks** against one shared multi-module fixture (`sample_repos/shopkit/`), graded with per-task `test_selector` so unrelated defects do not fail other tasks.

## Headline results

Measured with the real OpenAI client (`gpt-4.1-mini`), full 18-task suite, no prompt or agent-behavior changes for score chasing:

| Metric | Value |
|--------|-------|
| Tasks passed | 18 / 18 |
| Pass rate | 1.0 |
| Average steps | 7.28 |
| Average tool calls | 6.28 |
| Total failed tool calls | 0 |
| Average duration | ~7.3 s / task |

Failed task names: none. Numbers vary slightly across runs because model outputs are nondeterministic.

## Install

Requires Python 3.11+.

```bash
cd repopilot
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
pip install pytest
cp .env.example .env   # set OPENAI_API_KEY for live benchmarks
```

## Test

```bash
.venv/bin/python -m pytest
```

Unit and harness tests use scripted LLMs only — no live API calls.

## Run a benchmark

```bash
# load OPENAI_API_KEY from the environment or .env
set -a && source .env && set +a
PYTHONPATH=src .venv/bin/python scripts/run_benchmark.py
```

Print a detailed trace for selected tasks (default output stays concise):

```bash
.venv/bin/python scripts/run_benchmark.py --trace shipping_quote
```

`--trace` may be repeated for multiple task names.

## Documentation

- [docs/EVALUATION.md](docs/EVALUATION.md) — harness schemas, metrics, traces, isolation
- [docs/ROADMAP.md](docs/ROADMAP.md) — v1 complete vs future work
- [docs/DESIGN_DECISIONS.md](docs/DESIGN_DECISIONS.md) — architecture decision records
- [docs/ENGINEERING_PRINCIPLES.md](docs/ENGINEERING_PRINCIPLES.md) — delivery rules

## Status

**v1.0** — core agent loop, tools, OpenAI Responses client, workspace boundary, observer instrumentation, and deterministic 18-task eval harness are in place. Future GitHub workflow, persistence, and self-hosted inference are intentionally out of scope for this release; see the roadmap.
