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
