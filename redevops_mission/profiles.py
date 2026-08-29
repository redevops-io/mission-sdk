"""The local single-node profile — assemble and run a mission with zero infrastructure.

Builds a `MissionRuntime` from the authored operators + a local event ledger, drives it, and handles
human gates (park + report, or `--approve` to drive to completion). No standing services, no network.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ._bootstrap import ensure_runtime
from ._compile import build_registry, register_program_template
from .adapters import LocalEventLedger

ensure_runtime()

from agentic_os.mission.executor import Executor  # noqa: E402
from agentic_os.mission.operator_sdk import LocalOperatorClient  # noqa: E402
from agentic_os.mission.runtime import MissionRuntime  # noqa: E402


def local_runtime(operators, *, ledger_path: str | None = None, secure: bool = False,
                  sandbox=None, authority=None, concurrency: int | None = None):
    """A single-JVM-equivalent in-process runtime: registry + local operator client + event ledger.

    With ``secure=True`` the v0.3.x runtime security seams are wired from the authored capabilities'
    declared surface (``required_authority`` / ``isolation_class`` / ``network`` / ``data_classifications``):
      * a boundary ``SecurityMonitor`` emits telemetry the author never has to report (not agent-reported);
      * ``isolation_for`` routes an isolation-declaring capability through ``sandbox`` — and FAILS CLOSED
        if one declares isolation but no ``sandbox`` is wired (real confinement is the enterprise plane);
      * ``authority``, when given, enables the delegated-authority gate (a capability whose
        ``required_authority`` exceeds the leased chain is refused before its side effect).
    All opt-in: ``secure=False`` (the default) builds exactly the runtime as before."""
    registry = build_registry(operators)
    client = LocalOperatorClient({op.name: op for op in operators})
    store = LocalEventLedger(ledger_path).store()
    monitor = None
    ex_kwargs: dict = {}
    if secure:
        from agentic_os.mission.security_monitor import SecurityMonitor  # noqa: PLC0415 — opt-in
        monitor = SecurityMonitor(descriptor_for=registry.get)

        def isolation_for(node):
            spec = registry.get(node.capability)
            return (getattr(spec, "isolation_class", "") or "") if spec else ""

        def authority_for(node):
            spec = registry.get(node.capability)
            return tuple(getattr(spec, "required_authority", ()) or ()) if spec else ()

        ex_kwargs = {"sandbox": sandbox, "isolation_for": isolation_for, "monitor": monitor}
        if authority is not None:
            ex_kwargs["authority"] = authority
            ex_kwargs["authority_for"] = authority_for
    rt_kwargs: dict = {"store": store}
    if concurrency is not None:
        # Reach the runtime's built safe-parallel wave executor from the SDK boundary (not just the
        # AGENTIC_OS_MISSION_CONCURRENCY env). Independent ready nodes then run concurrently and commit in
        # deterministic causal order — plan fingerprint, node identity, idempotency, approvals and
        # event-sourced replay are unaffected (only wall-clock changes). Move BOTH knobs together: the wave
        # executor pool (max_concurrency) and how many the scheduler releases per wave (policy).
        from agentic_os.mission.scheduler import SchedulePolicy  # noqa: PLC0415
        rt_kwargs["max_concurrency"] = concurrency
        rt_kwargs["policy"] = SchedulePolicy(max_concurrency=concurrency)
    runtime = MissionRuntime(registry, Executor(client, **ex_kwargs), **rt_kwargs)
    runtime.security_monitor = monitor   # surfaced to run_program for the disposition/containment/spans
    return runtime


@dataclass
class RunResult:
    state: str
    succeeded: bool
    outcome: dict | None = None
    pending: list[dict] = field(default_factory=list)
    nodes_succeeded: int = 0
    approvals_applied: int = 0
    timeline: list[str] = field(default_factory=list)
    # ── security / telemetry (populated only on a `secure=True` run) ──
    disposition: str | None = None              # ALLOW | REQUIRE_REVIEW | NO_OVERRIDE | DENY
    containment: str | None = None              # RUNNING | CONTAINING | CONTAINED | REVIEW_REQUIRED | RECOVERED
    security_reasons: list[str] = field(default_factory=list)
    spans: list[dict] = field(default_factory=list)   # Mission-native trace tree (OTel-shaped)
    # ── scheduling (observable so the concurrency ceilings can't silently diverge) ──
    effective_concurrency: int = 1   # the limit that actually binds = min(executor pool, scheduler release)
    scheduler_policy: str = "serial"  # "serial" (=1) | "safe_parallel"
    scheduler_config: dict = field(default_factory=dict)   # the full startup config (requested/effective/bound_by/…)
    peak_parallelism: int = 1        # the MOST nodes actually released together in any wave (observed, not the cap)

    def to_text(self) -> str:
        lines = [f"run: {self.state.upper()}"
                 + (f"  ({self.approvals_applied} approval(s) applied)" if self.approvals_applied else "")]
        lines.append(f"  {self.nodes_succeeded} node(s) succeeded")
        if self.effective_concurrency > 1:
            lines.append(f"  scheduler: {self.scheduler_policy} (effective concurrency "
                         f"{self.effective_concurrency}, peak parallelism {self.peak_parallelism})")
        if self.pending:
            lines.append("  waiting on human decision:")
            for t in self.pending:
                lines.append(f"    ⏸ {t.get('capability')} — {t.get('prompt')}")
        if self.outcome and self.outcome.get("world"):
            for outcome, val in self.outcome["world"].items():
                lines.append(f"  ✓ {outcome}: {val}")
        if self.disposition is not None:
            mark = {"ALLOW": "✓", "REQUIRE_REVIEW": "⚠", "NO_OVERRIDE": "⛔", "DENY": "✗"}.get(self.disposition, "·")
            lines.append(f"  security: {mark} {self.disposition}"
                         + (f" · containment {self.containment}" if self.containment
                            and self.containment != "RUNNING" else "")
                         + (f" · {len(self.spans)} span(s)" if self.spans else ""))
            for r in self.security_reasons:
                lines.append(f"    — {r}")
        return "\n".join(lines)


def drive(program, operators, *, approve: bool = False, ledger_path: str | None = None,
          secure: bool = False, sandbox=None, authority=None, concurrency: int | None = None):
    """Create + run a mission on the local profile, applying human approvals if `approve`.
    Returns (runtime, mission_id, mission, approvals_applied) — the raw handle bundle/replay build on.
    `secure`/`sandbox`/`authority` opt into the v0.3.x runtime security seams (see `local_runtime`).
    `concurrency` (>1) runs independent ready nodes concurrently via the runtime's safe-parallel wave
    executor — replay/approval/exactly-once are preserved; default None keeps the runtime's own default."""
    rt = local_runtime(operators, ledger_path=ledger_path, secure=secure, sandbox=sandbox,
                       authority=authority, concurrency=concurrency)
    register_program_template(program)   # plan from the program's own steps, whatever its source
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


def run_program(program, operators, *, approve: bool = False, ledger_path: str | None = None,
                secure: bool = False, sandbox=None, authority=None, concurrency: int | None = None) -> RunResult:
    rt, mid, m, approvals = drive(program, operators, approve=approve, ledger_path=ledger_path,
                                  secure=secure, sandbox=sandbox, authority=authority, concurrency=concurrency)
    pending = [t for t in rt.inbox() if t["mission_id"] == mid]
    events = rt.repo.timeline(mid)
    timeline = [e["type"] for e in events]
    waves = [e["payload"] for e in events if e["type"] == "WaveScheduled"]
    peak = max((w.get("peak_parallel_nodes", 0) for w in waves), default=1)
    cfg = next((e["payload"] for e in events if e["type"] == "SchedulerConfigured"), None)
    if cfg is None and hasattr(rt, "scheduler_config"):
        cfg = rt.scheduler_config()
    result = RunResult(
        state=m.state.value,
        succeeded=m.state.value == "succeeded",
        outcome=m.outcome,
        pending=pending,
        nodes_succeeded=timeline.count("NodeSucceeded"),
        approvals_applied=approvals,
        timeline=timeline,
        effective_concurrency=getattr(rt, "effective_max_concurrency", 1),
        scheduler_policy=("safe_parallel" if getattr(rt, "effective_max_concurrency", 1) > 1 else "serial"),
        scheduler_config=cfg or {},
        peak_parallelism=max(1, peak),
    )
    # Fold in the security assessment: correlate the boundary telemetry into a disposition, drive
    # containment, and surface the Mission-native trace tree. Only when a secure run produced events.
    monitor = getattr(rt, "security_monitor", None)
    if monitor is not None and getattr(monitor.trajectory, "events", None):
        disposition, reasons, cstate = monitor.enforce()
        result.disposition = disposition.value
        result.containment = cstate.value
        result.security_reasons = list(reasons)
        from agentic_os.mission.tracing import MissionTrace  # noqa: PLC0415 — opt-in
        result.spans = MissionTrace(mid).spans(monitor.trajectory)
    return result
