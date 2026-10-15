"""02_governed_quickstart — a MissionProgram with an authorization gate, explain, and a verifiable receipt.

One two-step mission: draft a notice (no side effect), then publish it (a side-effecting capability that
requires human approval). The script shows, offline and with no provider key:

  1. the plan, via ``explain`` (no execution);
  2. the run PARKING at the approval gate when nobody has approved;
  3. the run completing once the gate is approved;
  4. the "receipt": the sealed, self-verifying case bundle (``export_bundle`` + ``verify_bundle``) and a
     replay that reproduces the recorded terminal state.

Note on wording: the SDK has no class called "receipt". In this example "receipt" means the sealed
``CaseBundle`` returned by ``export_bundle`` and checked by ``verify_bundle``.

    python examples/02_governed_quickstart/main.py
"""
from __future__ import annotations

from redevops_mission import (
    MissionProgram, Operator, capability, step, template,
    run_program, explain, export_bundle, verify_bundle, replay_bundle,
)


@template("publish_notice")
def publish_notice(mission_id):
    return [
        step("notice_drafted", need="draft the notice text"),
        step("notice_published", need="publish the notice to subscribers",
             after=["notice_drafted"],
             constraints=["external side effect - requires human approval"]),
    ]


OPERATORS = [
    Operator("comms", [
        capability("notice.draft", handler=lambda i: {"text": "Maintenance window on Friday"},
                   provides=["notice_drafted"], permissions=["notice:draft"]),
        capability("notice.publish", handler=lambda i: {"published": True},
                   provides=["notice_published"], permissions=["notice:publish"],
                   side_effecting=True, approval_required=True, undo="notice.retract"),
    ]),
]

# The authorization surface: the program is granted exactly these permissions.
GRANTS = ["notice:draft", "notice:publish"]
PROGRAM = MissionProgram.from_template("publish_notice", goal="Publish the maintenance notice", grants=GRANTS)


def main() -> None:
    # 1. EXPLAIN - the compiled plan; nothing runs.
    exp = explain(PROGRAM, OPERATORS)
    print(f"explain  : goal={exp.goal!r}, {len(exp.nodes)} node(s)")
    for n in exp.nodes:
        print(f"           {n['capability']} -> {n['produces']}")

    # 2. RUN WITHOUT APPROVAL - the gate must hold; the side-effecting step must not fire.
    parked = run_program(PROGRAM, OPERATORS)
    print(f"no approval : state={parked.state} succeeded={parked.succeeded} pending_gates={len(parked.pending)}")

    # 3. RUN WITH APPROVAL - the gate is driven to completion.
    done = run_program(PROGRAM, OPERATORS, approve=True)
    print(f"approved    : state={done.state} succeeded={done.succeeded} approvals_applied={done.approvals_applied}")

    # 4. RECEIPT - sealed bundle, verified without re-running, then replayed.
    bundle = export_bundle(PROGRAM, OPERATORS)
    report = verify_bundle(bundle)
    replay = replay_bundle(bundle, OPERATORS)
    print(f"receipt     : integrity_ok={report.integrity_ok} succeeded={report.succeeded}")
    print(f"replay      : recorded={replay.recorded_state} replayed={replay.replayed_state} "
          f"consistent={replay.consistent}")

    assert not parked.succeeded and parked.pending, "an unapproved gate must park the run"
    assert done.succeeded and done.approvals_applied >= 1, "an approved gate must complete the run"
    assert report.integrity_ok and replay.consistent, "the receipt must verify and replay"
    print("\nOK - planned, gated, approved, sealed, verified, replayed.")


if __name__ == "__main__":
    main()
