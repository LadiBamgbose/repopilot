# Engineering Principles

Rules that guide how RepoPilot is built and reviewed.

## Tools and runtime

- **One capability per tool.** Each tool does one job and returns a
  `ToolResult`. Prefer composing tools in the agent over packing multiple
  behaviors into one function.
- **Tools never talk to the LLM.** Tools perform local work (filesystem, git,
  tests). Model I/O belongs in the agent / LLM layer.
- **Agent orchestration lives outside tools.** Planning, retries, and control
  flow sit above `execute_tool`, not inside individual tools.
- **One tool call per agent step.** The runner and OpenAI client stay aligned
  (`parallel_tool_calls=False`) so conversation state and traces stay linear.
- **Every tool requires unit tests.** Cover success paths and important failure
  modes (missing files, path escape, invalid input) before expanding scope.

## Determinism and evaluation

- **Deterministic code for deterministic responsibilities.** Path checks,
  registry dispatch, scoring, metric aggregation, and fixture isolation must
  not depend on model creativity. Keep nondeterminism inside the LLM client.
- **Pytest is the benchmark source of truth.** Do not substitute LLM judging or
  agent self-report for `tests_passed`.
- **Instrument via observers.** Metrics and traces subscribe to agent events;
  they must not change prompts, tools, or loop policy.
- **Automated tests never call real model APIs.** Use scripted LLMs in unit and
  harness tests; reserve live OpenAI runs for explicit benchmark scripts.

## Design and delivery

- **Prefer explicit over implicit behavior.** Pass dependencies such as
  `Workspace` deliberately. Avoid hidden globals and cwd-based assumptions.
- **Build the minimum abstraction required today.** Add structure when it
  removes real duplication or clarifies boundaries—not in anticipation of
  distant features.
- **Favor readability over cleverness.** Straightforward code that a reviewer
  can follow in one pass beats compact indirection.
- **Small pull requests.** Ship focused changes that are easy to review and
  revert.
- **Architecture decisions should be documented.** Record meaningful choices in
  `docs/DESIGN_DECISIONS.md` so future work inherits the rationale, not just the
  outcome.
