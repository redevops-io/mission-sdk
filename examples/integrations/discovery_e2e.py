"""Discovery Runtime → the one compilation path — a REAL end-to-end (design §13.3).

Drives the actual `DiscoveryRuntime` (enterprise), takes the proposal it produces, and runs it through
the SDK's `MissionProgram.from_discovery(...)` so a *discovered* mission validates / runs / gates
exactly like a hand-authored one, carrying the proposal as its `origin` (the "why").

NOT part of the SDK's pytest suite — it requires the enterprise `agentic-os` (the Discovery Runtime is
enterprise-only, absent from the pinned public runtime). Run it against an enterprise checkout:

    PYTHONPATH=/path/to/agentic-os-src:/path/to/mission-sdk python3 examples/integrations/discovery_e2e.py

Finding it demonstrates: Discovery's `suggest_template` emits an *opportunity-class label*, not a
registered template — so putting Discovery on the deterministic one-path needs an
opportunity-class → registered-template mapping (the SDK compiles no-LLM, so it needs steps). Here that
mapping is a generic investigation template; in production it belongs in the Discovery integration.
"""
from __future__ import annotations

import dataclasses

from agentic_os.discovery import (  # enterprise runtime
    Correlator, DetectionEngine, DeterministicHypothesisPlanner, ProposalPolicy, ProposalScorer,
    Signal, SignalStore, default_detectors,
)
from redevops_mission import (
    MissionProgram, Operator, capability, export_bundle, mission_ci, step, template, validate,
)


def real_proposal():
    s = SignalStore()
    for i, v in enumerate([100] * 8 + [40]):          # a conversion drop → anomaly
        s.observe(Signal(source="metrics", subject="store.1", metric="conversion",
                         value=float(v), observed_at=1000.0 + i * 3600.0, confidence=0.9))
    dets = DetectionEngine(default_detectors()).scan(s)
    kept, _ = Correlator(clock=lambda: 0.0).suppress(dets)
    group = Correlator(clock=lambda: 0.0).correlate(kept)[0]
    p = ProposalScorer().build(DeterministicHypothesisPlanner().plan(group), group)
    ProposalPolicy().decide(p)
    return p


def main() -> None:
    p = real_proposal()
    print(f"REAL Discovery proposal: template={p.suggested_template!r} class={p.opportunity_class!r} "
          f"decision={p.decision}")

    # opportunity-class → a registered investigation template (the mapping the integration supplies)
    @template(p.suggested_template)
    def _investigation(mission_id):
        return [
            step("evidence_gathered", need="gather evidence for the detected anomaly"),
            step("impact_assessed", need="assess the material impact", after=["evidence_gathered"]),
            step("remediation_done", need="remediate the root cause", after=["impact_assessed"],
                 constraints=["consequential — requires human approval"]),
        ]

    program = MissionProgram.from_discovery(dataclasses.asdict(p), grants=[])
    ops = [Operator("disc", [capability(f"stub.{st.outcome}", handler=lambda i: {"ok": True},
                                        provides=[st.outcome]) for st in program.steps])]

    assert program.source == "discovery" and program.origin["ref"] == p.id
    assert validate(program, ops).passed
    ci = mission_ci(program, ops)
    assert ci.passed, ci.checks
    bundle = export_bundle(program, ops)
    assert bundle.state == "succeeded" and bundle.origin["ref"] == p.id
    print(f"→ ran through the SDK one-path: state={bundle.state} ci={ci.passed} "
          f"origin={bundle.origin['kind']}:{bundle.origin['ref']}")
    print("OK — a discovered mission validates/runs/gates identically to a hand-authored one.")


if __name__ == "__main__":
    main()
