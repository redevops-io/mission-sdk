"""00_minimal — the smallest complete Mission SDK example.

Author a one-step mission, execute it, explain the plan, then replay it and verify the replay reproduced
the sealed run. No side effects, no approvals, no provider keys, no network — fully offline and
deterministic, so it works from a clean `pip install` and runs in CI.

    python examples/00_minimal/main.py
"""
from __future__ import annotations

from redevops_mission import (
    MissionProgram, Operator, capability, step, template,
    run_program, explain, export_bundle, replay_bundle, verify_bundle,
)


# ── 1. the mission: the outcomes to produce and their dependency shape ───────────────────────────────
@template("hello_mission")
def hello_mission(mission_id):
    return [
        step("greeting_ready", need="produce a greeting for the user"),
    ]


# ── 2. the capability that provides the outcome (a plain function — your existing logic) ──────────────
OPERATORS = [
    Operator("greeter", [
        capability("greet.hello",
                   handler=lambda inputs: {"greeting": "hello from the ReDevOps Mission Runtime"},
                   provides=["greeting_ready"]),
    ]),
]

# ── 3. the one public artifact: a versioned MissionProgram ───────────────────────────────────────────
PROGRAM = MissionProgram.from_template("hello_mission", goal="Greet the user", grants=[])


def main() -> None:
    # Execute — plans the mission, runs the capability, seals the run.
    result = run_program(PROGRAM, OPERATORS)
    print(f"run        : state={result.state} succeeded={result.succeeded} "
          f"nodes={result.nodes_succeeded}")

    # Explain — the compiled physical plan (which capability produces each outcome, and its shape).
    exp = explain(PROGRAM, OPERATORS)
    print(f"explain    : goal={exp.goal!r}, {len(exp.nodes)} node(s), "
          f"first={exp.nodes[0]['capability']} -> {exp.nodes[0]['produces']}")

    # Replay — rebuild the run from its portable bundle and confirm it reproduces the sealed terminal state.
    bundle = export_bundle(PROGRAM, OPERATORS)
    replay = replay_bundle(bundle, OPERATORS)
    print(f"replay     : recorded={replay.recorded_state} replayed={replay.replayed_state} "
          f"consistent={replay.consistent} integrity_ok={replay.integrity_ok}")

    # Verify — the bundle is self-verifying (integrity + verifications) without re-running.
    report = verify_bundle(bundle)
    print(f"verify     : succeeded={report.succeeded} integrity_ok={report.integrity_ok} "
          f"verifications={report.verifications}")

    # The core guarantee: replay reproduces the sealed run.
    assert result.succeeded, "the minimal mission should succeed"
    assert replay.consistent and replay.integrity_ok, "replay must reproduce the sealed run"
    assert replay.recorded_state == replay.replayed_state, "replayed terminal state must match the record"
    print("\nOK — mission executed, explained, replayed, and verified.")


if __name__ == "__main__":
    main()
