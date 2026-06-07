# RepoPilot

RepoPilot is an Applied AI Engineering portfolio project. It will become an AI coding agent that takes a GitHub issue, inspects a local repo, selects relevant files, creates a plan, edits code, runs tests, retries after failure, logs all events, and produces a PR-style report.

## Vision

Build a transparent, testable AI coding agent that demonstrates production-oriented applied AI engineering: structured planning, tool use, failure recovery, event logging, and measurable evaluation.

## What RepoPilot Will Demonstrate

- Multi-step agent orchestration for real software tasks
- Context selection over large local repositories
- Safe file search, read, and edit tooling
- Test-driven validation with retry loops
- Structured event logging and cost tracking
- Benchmark-driven evaluation and PR-style reporting

## Planned Architecture

```
                ┌─────────────┐
                │ GitHub Issue│
                └──────┬──────┘
                       │
                       ▼
            ┌────────────────────┐
            │ Planning Agent     │
            └─────────┬──────────┘
                      │
          Creates structured plan
                      │
                      ▼
       ┌────────────────────────────┐
       │ Context Selection Agent    │
       └─────────────┬──────────────┘
                     │
             Finds relevant files
                     │
                     ▼
       ┌────────────────────────────┐
       │ Editing Agent              │
       └─────────────┬──────────────┘
                     │
              Creates patch
                     │
                     ▼
       ┌────────────────────────────┐
       │ Test Execution Agent       │
       └─────────────┬──────────────┘
                     │
              Runs pytest
                     │
          ┌──────────┴─────────┐
          │                    │
      PASS                    FAIL
          │                    │
          ▼                    ▼
   Final Report        Failure Analysis
                               │
                               ▼
                       Retry Planning
                               │
                               ▼
                          Edit Again
```

## Current Status

Initial project skeleton only. No agent logic, LLM clients, or API server implemented yet.
