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

SCHEMA_VERSION = "0.2"
# Everything a reader relies on is under the digest. Schema 0.1 hashed the events only (and kept 64 bits of the hash), so the recorded state and
# outcome of a bundle could be edited without the digest noticing.
_SEALED = ("schema_version", "program", "goal", "mission_id", "state", "outcome", "events", "steps", "source", "origin")


def _digest_events(events: list[dict]) -> str:
    """Schema 0.1: the events only, 64 bits. Kept so older bundles still load and check."""
    return hashlib.sha256(json.dumps(events, sort_keys=True, default=str).encode()).hexdigest()[:16]


def _digest(doc: dict) -> str:
    """Schema 0.2: SHA-256 over every sealed field. It detects a change made after export. It is not a signature: whoever can rewrite the bundle can
    also recompute it, so a bundle from a party you do not trust needs a signature over the file, which this SDK does not provide."""
    body = {k: doc.get(k) for k in _SEALED}
    return "sha256:" + hashlib.sha256(json.dumps(body, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()


def _state_in_events(events: list[dict]):
    """The mission state the event log itself ends in (the last MissionStateChanged), or None when the log records none."""
    for e in reversed(events):
        if e.get("type") == "MissionStateChanged" and isinstance(e.get("payload"), dict) and "state" in e["payload"]:
            return str(e["payload"]["state"])
    return None


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
        b = cls(program=program, goal=goal, mission_id=mission_id, state=state, outcome=outcome,
                events=evs, steps=list(steps or []), source=source, origin=origin)
        b.digest = b._expected_digest()
        return b

    def _expected_digest(self) -> str:
        if self.schema_version == "0.1":
            return _digest_events(self.events)
        return _digest(json.loads(json.dumps(asdict(self), default=str)))          # the same normal form a reloaded bundle has

    def integrity_ok(self) -> bool:
        """Nothing under the digest changed since the bundle was built: goal, state, outcome, events, steps and origin (schema 0.1: the events only).
        A digest is not a signature; see `_digest`."""
        return bool(self.digest) and self.digest == self._expected_digest()

    def state_matches_events(self) -> bool:
        """The recorded terminal state is the one the event log ends in. Holds for every schema, so an edited `state` is caught in a 0.1 bundle too."""
        return _state_in_events(self.events) == self.state

    def sealed_fields(self) -> str:
        return "events only (schema 0.1)" if self.schema_version == "0.1" else "state, outcome, events, steps, origin"

    def timeline(self) -> list[str]:
        return [e["type"] for e in self.events]

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(asdict(self), indent=indent, sort_keys=True, default=str)

    @classmethod
    def from_json(cls, text: str) -> "CaseBundle":
        d = json.loads(text)
        return cls(**{k: d[k] for k in ("program", "goal", "mission_id", "state", "outcome", "events",
                                        "steps", "source", "origin", "digest") if k in d},
                   schema_version=str(d.get("schema_version", "0.1")))          # a bundle that names no schema predates 0.2


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
    integrity = bundle.integrity_ok() and bundle.state_matches_events()
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
    sealed: str = ""                 # what the digest covers in this bundle

    def to_text(self) -> str:
        return "\n".join([
            f"verify: {'PASS' if self.succeeded and self.integrity_ok else 'FAIL'}",
            f"  terminal success     {self.succeeded}",
            f"  ledger integrity     {'ok' if self.integrity_ok else 'TAMPERED'}" + (f"  (digest covers: {self.sealed})" if self.sealed else ""),
            f"  verifications run     {self.verifications}",
            f"  nodes succeeded       {self.nodes_succeeded}",
        ])


def verify_bundle(bundle: CaseBundle) -> VerifyReport:
    """Report what the runtime actually recorded: terminal success, ledger integrity, and the count of
    verification stages that ran and nodes that succeeded."""
    types = bundle.timeline()
    # Success is what the event log ends in, and the recorded state has to agree with it: a `state` field that says more than the events do is a
    # changed bundle, whatever its digest.
    consistent = bundle.state_matches_events()
    return VerifyReport(
        succeeded=consistent and bundle.state == "succeeded",
        integrity_ok=bundle.integrity_ok() and consistent,
        sealed=bundle.sealed_fields(),
        verifications=types.count("VerificationRecorded"),
        nodes_succeeded=types.count("NodeSucceeded"),
    )
