"""Live smoke test against sample_repos/calculator_bug.

Run from the repository root:

    PYTHONPATH=src python scripts/smoke_calculator.py

The API key is read by the OpenAI SDK from OPENAI_API_KEY.
Override the model with OPENAI_MODEL.
"""

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from repopilot.agent.observer import ConsoleAgentObserver
from repopilot.agent.runner import run_agent
from repopilot.llm.openai_client import OpenAIClient
from repopilot.workspace import Workspace

SAMPLE_ROOT = REPO_ROOT / "sample_repos" / "calculator_bug"
MODEL = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")
TASK = (
    "Fix the failing calculator test. Inspect the repository, "
    "make the smallest correct change, run the tests, and stop when they pass."
)


def main() -> None:
    workspace = Workspace(SAMPLE_ROOT)
    if workspace.root != SAMPLE_ROOT.resolve():
        raise SystemExit(f"Refusing to run: workspace root is {workspace.root}")
    if workspace.root == REPO_ROOT:
        raise SystemExit("Refusing to run against the RepoPilot repository root")

    llm = OpenAIClient(model=MODEL)
    result = run_agent(
        TASK,
        llm=llm,
        workspace=workspace,
        observer=ConsoleAgentObserver(),
    )
    print(result)


if __name__ == "__main__":
    main()
