"""Case bundles, replay, diff, verify (M2).

A `CaseBundle` is a portable, self-verifying record of one mission run: its goal, terminal state,
outcome, and the full event-sourced history, plus a content digest. From it you can **replay** (rebuild
a fresh runtime from the events and confirm it reaches the same terminal state — the event log is a
faithful record), **diff** two runs, and **verify** what the runtime recorded.

Built over the Mission Runtime's operational `EventStore` — the history `run` actually produces. (The
v10 `events.py` RuntimeEvent `MissionCaseBundle` is a separate, not-yet-wired construct; when it lands
in the runtime this becomes an adapter over it.)
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field

from ._bootstrap import ensure_runtime
from ._compile import build_registry, register_steps_template

SCHEMA_VERSION = "0.1"


def _digest(events: list[dict]) -> str:
    return hashlib.sha256(json.dumps(events, sort_keys=True, default=str).encode()).hexdigest()[:16]


@dataclass
class CaseBundle:
    program: str
    goal: str
    mission_id: str
    state: str
    outcome: dict | None
    events: list[dict] = field(default_factory=list)   # [{seq, type, payload}]
    steps: list[dict] = field(default_factory=list)     # the mission definition (so replay is self-contained)
    source: str = "human:template"                       # the kind of author
    origin: dict | None = None                           # the triggering record (the "why")
    digest: str = ""
    schema_version: str = SCHEMA_VERSION

    @classmethod
    def from_run(cls, program: str, goal: str, mission_id: str, state: str, outcome: dict | None,
                 events, steps: list[dict] | None = None, source: str = "human:template",
                 origin: dict | None = None) -> "CaseBundle":
        evs = [{"seq": e.seq, "type": e.type, "payload": e.payload} for e in events]
        return cls(program=program, goal=goal, mission_id=mission_id, state=state, outcome=outcome,
                   events=evs, steps=list(steps or []), source=source, origin=origin, digest=_digest(evs))

    def integrity_ok(self) -> bool:
        """The events have not been tampered with since the bundle was built."""
        return self.digest == _digest(self.events)

    def timeline(self) -> list[str]:
        return [e["type"] for e in self.events]

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(asdict(self), indent=indent, sort_keys=True, default=str)

    @classmethod
    def from_json(cls, text: str) -> "CaseBundle":
        d = json.loads(text)
        return cls(**{k: d[k] for k in ("program", "goal", "mission_id", "state", "outcome", "events",
                                        "steps", "source", "origin", "digest", "schema_version") if k in d})


# ---- build -------------------------------------------------------------------------------------------
def export_bundle(program, operators, *, approve: bool = True, ledger_path: str | None = None) -> CaseBundle:
    """Run the mission (auto-approving gates by default so it reaches a terminal state) and bundle it."""
    from ._compile import program_step_dicts
    from .profiles import drive

    rt, mid, m, _ = drive(program, operators, approve=approve, ledger_path=ledger_path)
    return CaseBundle.from_run(program.name, program.goal, mid, m.state.value, m.outcome,
                               rt.store.for_mission(mid), steps=program_step_dicts(program),
                               source=program.source, origin=program.origin)


# ---- replay ------------------------------------------------------------------------------------------
@dataclass
class ReplayResult:
    integrity_ok: bool
    recorded_state: str
    replayed_state: str
    consistent: bool
    events: int = 0

    def to_text(self) -> str:
        mark = "CONSISTENT" if self.consistent else "INCONSISTENT"
        return "\n".join([
            f"replay: {mark}",
            f"  integrity (digest)   {'ok' if self.integrity_ok else 'TAMPERED'}",
            f"  recorded state       {self.recorded_state}",
            f"  replayed state       {self.replayed_state}  ({self.events} events rehydrated)",
        ])


def replay_bundle(bundle: CaseBundle, operators) -> ReplayResult:
    """Reconstruct a fresh runtime from the bundle's events and rehydrate the mission — the terminal
    state it recovers must match what was recorded (the event log is a faithful, replayable record)."""
    ensure_runtime()
    from agentic_os.mission.executor import Executor
    from agentic_os.mission.operator_sdk import LocalOperatorClient
    from agentic_os.mission.runtime import MissionRuntime
    from agentic_os.mission.store import EventStore

    # The runtime's rehydrate re-compiles the plan, so the template must be present even in a fresh
    # process. The bundle carries its own step definitions, so replay is self-contained.
    if bundle.steps:
        register_steps_template(bundle.program, bundle.steps)

    store = EventStore()
    for e in bundle.events:
        store.append(e["type"], bundle.mission_id, e["payload"])
    rt = MissionRuntime(build_registry(operators),
                        Executor(LocalOperatorClient({op.name: op for op in operators})), store=store)
    m = rt.rehydrate(bundle.mission_id)
    integrity = bundle.integrity_ok()
    return ReplayResult(
        integrity_ok=integrity,
        recorded_state=bundle.state,
        replayed_state=m.state.value,
        consistent=integrity and m.state.value == bundle.state,
        events=len(bundle.events),
    )


# ---- diff --------------------------------------------------------------------------------------------
def diff_bundles(a: CaseBundle, b: CaseBundle) -> dict:
    """Structural differences between two runs — only what changed is reported."""
    d: dict = {}
    if a.state != b.state:
        d["state"] = {"a": a.state, "b": b.state}
    if a.goal != b.goal:
        d["goal"] = {"a": a.goal, "b": b.goal}
    ta, tb = a.timeline(), b.timeline()
    if ta != tb:
        d["event_count"] = {"a": len(ta), "b": len(tb)}
        first = next((i for i, (x, y) in enumerate(zip(ta, tb)) if x != y), min(len(ta), len(tb)))
        d["first_divergence"] = {"index": first,
                                 "a": ta[first] if first < len(ta) else None,
                                 "b": tb[first] if first < len(tb) else None}
    wa = (a.outcome or {}).get("world", {})
    wb = (b.outcome or {}).get("world", {})
    if wa != wb:
        d["outcome_world"] = {"only_a": sorted(set(wa) - set(wb)),
                              "only_b": sorted(set(wb) - set(wa)),
                              "changed": sorted(k for k in set(wa) & set(wb) if wa[k] != wb[k])}
    return d


def diff_text(d: dict) -> str:
    if not d:
        return "diff: identical (state, timeline, and outcome all match)"
    lines = ["diff:"]
    for k, v in d.items():
        lines.append(f"  {k}: {v}")
    return "\n".join(lines)


# ---- verify ------------------------------------------------------------------------------------------
@dataclass
class VerifyReport:
    succeeded: bool
    integrity_ok: bool
    verifications: int
    nodes_succeeded: int

    def to_text(self) -> str:
        return "\n".join([
            f"verify: {'PASS' if self.succeeded and self.integrity_ok else 'FAIL'}",
            f"  terminal success     {self.succeeded}",
            f"  ledger integrity     {'ok' if self.integrity_ok else 'TAMPERED'}",
            f"  verifications run     {self.verifications}",
            f"  nodes succeeded       {self.nodes_succeeded}",
        ])


def verify_bundle(bundle: CaseBundle) -> VerifyReport:
    """Report what the runtime actually recorded: terminal success, ledger integrity, and the count of
    verification stages that ran and nodes that succeeded."""
    types = bundle.timeline()
    return VerifyReport(
        succeeded=bundle.state == "succeeded",
        integrity_ok=bundle.integrity_ok(),
        verifications=types.count("VerificationRecorded"),
        nodes_succeeded=types.count("NodeSucceeded"),
    )
