# Evaluation

How RepoPilot scores coding-agent runs without an LLM judge.

## Design goal

Evaluation answers two different questions:

1. **Did the fix work?** → pytest exit code after the agent finishes.
2. **How did the agent behave?** → steps, tool usage, failures, duration, and optional step traces.

Those concerns stay separate so a chatty but correct run still passes, and a confident but broken run still fails.

## Schemas

### `BenchmarkTask`

One controlled coding task loaded from a fixture directory.

| Field | Meaning |
|-------|---------|
| `name` | Stable task id (e.g. `shipping_quote`, `loyalty_discount`) |
| `fixture_dir` | Source tree copied into a temp workspace for the run |
| `prompt` | Task text given to the agent (from `task.txt` or ShopKit `tasks/*.txt`) |
| `test_selector` | Optional pytest path/node id for harness grading only |

### `AgentResult`

Outcome of `run_agent` alone: whether the loop returned a final answer, step count, and any loop error (for example max steps exceeded). This is **not** the benchmark pass bit.

### `TaskEvalResult`

One scored task after the agent run and harness pytest:

| Field | Meaning |
|-------|---------|
| `tests_passed` | `True` iff harness pytest exited 0 |
| `steps` | Steps reported by `AgentResult` |
| `failure_reason` | Agent-loop failure or pytest failure summary |
| `tool_calls` / `tool_usage` / `tool_failures` | From `BenchmarkMetricsObserver` |
| `duration_ms` | Wall time for the agent run |
| `trace` | Bounded `TraceEvent` list from `BenchmarkTraceObserver` |

Pass/fail is never derived from trace contents.

### `EvalSummary`

Aggregate over a list of `TaskEvalResult` values: totals, pass rate, average steps / tool calls / duration, total failed tool calls, and failed task names.

## Pytest as the source of truth

After each agent run, the harness calls `score_tests` in the temp workspace:

- mini-repo tasks: full suite under that fixture
- ShopKit tasks: pytest restricted by `test_selector`

A task passes only when that process returns exit code 0. There is no second-model “did this look fixed?” step.

Agent-invoked `run_tests` is a tool the model may call during the loop. Harness scoring is separate and always runs once after the agent stops.

## `test_selector` and ShopKit

ShopKit is one shared multi-module repo with several independent defects present at once. If every task graded the full suite, fixing loyalty would still fail payment tests and every task would look broken.

Each ShopKit `BenchmarkTask` therefore sets `test_selector` to the pytest file for that defect (for example `tests/test_loyalty_discount.py`). The agent still sees the whole repo copy; only harness grading is scoped.

Prompt files under `tasks/` are excluded from workspace copies so the agent cannot read the grading prompt from disk.

## Metrics

`BenchmarkMetricsObserver` listens to agent events:

- `tool_calls` / `tool_usage` count `ToolCallRequested` events
- `tool_failures` count `ToolResultReturned` with `success=False`

Failed pytest inside a successful `run_tests` tool call is **not** a tool failure: the tool ran correctly and reported a non-zero exit code. Inefficiency shows up in steps, tool usage, and traces instead.

## Detailed trace observer

`BenchmarkTraceObserver` records bounded `TraceEvent` rows for:

- model responses
- tool calls (name, truncated args, file `path` when present)
- tool results (success, short summary, `exit_code` / `failure_summary` for `run_tests`)
- final answers

CLI default output stays one line per task. Print traces only when requested:

```bash
.venv/bin/python scripts/run_benchmark.py --trace shipping_quote
```

Traces are in-memory for the run. There is no database or persistence layer yet.

## Isolation and reset

For each task, `run_benchmark`:

1. creates a fresh temporary directory
2. copies the fixture (skipping `.git`, caches, `task.txt`, and ShopKit `tasks/`)
3. constructs a new metrics observer and a new trace observer
4. runs the agent, then scores with pytest
5. discards the temp tree

Source fixtures under `sample_repos/` are not mutated. Metrics and traces do not accumulate across tasks.

## Limitations

- **Model nondeterminism.** The same task can take different paths, step counts, and durations across runs. Pass rate is more stable than efficiency metrics when the suite is green.
- **No LLM judge.** Semantic quality beyond “tests pass” is out of scope.
- **No cost accounting yet.** Duration is wall clock; token/cost tracking is future work.
- **Temp-copy isolation only.** There is no durable run history store.
- **Live benchmarks need network and `OPENAI_API_KEY`.** Automated unit tests use scripted LLMs and never call OpenAI.
