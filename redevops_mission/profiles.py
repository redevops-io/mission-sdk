"""The local single-node profile — assemble and run a mission with zero infrastructure.

Builds a `MissionRuntime` from the authored operators + a local event ledger, drives it, and handles
human gates (park + report, or `--approve` to drive to completion). No standing services, no network.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ._bootstrap import ensure_runtime
from ._compile import build_registry
from .adapters import LocalEventLedger

ensure_runtime()

from agentic_os.mission.executor import Executor  # noqa: E402
from agentic_os.mission.operator_sdk import LocalOperatorClient  # noqa: E402
from agentic_os.mission.runtime import MissionRuntime  # noqa: E402


def local_runtime(operators, *, ledger_path: str | None = None):
    """A single-JVM-equivalent in-process runtime: registry + local operator client + event ledger."""
    registry = build_registry(operators)
    client = LocalOperatorClient({op.name: op for op in operators})
    store = LocalEventLedger(ledger_path).store()
    return MissionRuntime(registry, Executor(client), store=store)


@dataclass
class RunResult:
    state: str
    succeeded: bool
    outcome: dict | None = None
    pending: list[dict] = field(default_factory=list)
    nodes_succeeded: int = 0
    approvals_applied: int = 0
    timeline: list[str] = field(default_factory=list)

    def to_text(self) -> str:
        lines = [f"run: {self.state.upper()}"
                 + (f"  ({self.approvals_applied} approval(s) applied)" if self.approvals_applied else "")]
        lines.append(f"  {self.nodes_succeeded} node(s) succeeded")
        if self.pending:
            lines.append("  waiting on human decision:")
            for t in self.pending:
                lines.append(f"    ⏸ {t.get('capability')} — {t.get('prompt')}")
        if self.outcome and self.outcome.get("world"):
            for outcome, val in self.outcome["world"].items():
                lines.append(f"  ✓ {outcome}: {val}")
        return "\n".join(lines)


def drive(program, operators, *, approve: bool = False, ledger_path: str | None = None):
    """Create + run a mission on the local profile, applying human approvals if `approve`.
    Returns (runtime, mission_id, mission, approvals_applied) — the raw handle bundle/replay build on."""
    rt = local_runtime(operators, ledger_path=ledger_path)
    mission = rt.create_mission(program.goal, policy_refs=list(program.grants), template=program.name)
    m = rt.run(mission.id)

    approvals = 0
    while approve and m.state.value == "waiting_human":
        tasks = [t for t in rt.inbox() if t["mission_id"] == mission.id]
        if not tasks:
            break
        for t in tasks:
            m = rt.approve(mission.id, t["node_id"], "approve")
            approvals += 1
    return rt, mission.id, m, approvals


def run_program(program, operators, *, approve: bool = False, ledger_path: str | None = None) -> RunResult:
    rt, mid, m, approvals = drive(program, operators, approve=approve, ledger_path=ledger_path)
    pending = [t for t in rt.inbox() if t["mission_id"] == mid]
    timeline = [e["type"] for e in rt.repo.timeline(mid)]
    return RunResult(
        state=m.state.value,
        succeeded=m.state.value == "succeeded",
        outcome=m.outcome,
        pending=pending,
        nodes_succeeded=timeline.count("NodeSucceeded"),
        approvals_applied=approvals,
        timeline=timeline,
    )
