"""01_existing_agent — keep your agent, add the runtime.

An existing agent function stays exactly as it is; ReDevOps wraps the *runtime concerns* around it — a
governed plan, execution, verification, and replay — by putting the existing call inside a `capability`
handler. Nothing about the agent changes. Offline + deterministic.

    python examples/01_existing_agent/main.py
"""
from __future__ import annotations

from redevops_mission import (
    MissionProgram, Operator, capability, step, template, run_program, export_bundle, replay_bundle,
)


# ── your existing agent — UNCHANGED. Could be a LangGraph/LangChain/custom agent invoke() call. ──────
def answer(prompt: str) -> str:
    return f"[existing-agent] answer to: {prompt}"


# ── the ONLY addition: wrap the existing call in a capability handler. The agent is not rewritten. ───
@template("agent_mission")
def agent_mission(mission_id):
    return [step("answer_ready", need="answer the user's prompt with the existing agent")]


OPERATORS = [
    Operator("my_app", [
        capability("app.answer",
                   handler=lambda inputs: {"answer": answer(inputs.get("prompt", "what is ReDevOps?"))},
                   provides=["answer_ready"]),
    ]),
]

PROGRAM = MissionProgram.from_template(
    "agent_mission", goal="Answer the user with the existing agent", grants=[],
)


def main() -> None:
    # BEFORE (still valid on its own): result = answer("what is ReDevOps?")
    # AFTER: the same call, now executed as a governed, replayable mission.
    result = run_program(PROGRAM, OPERATORS)
    print(f"run     : state={result.state} succeeded={result.succeeded}")

    replay = replay_bundle(export_bundle(PROGRAM, OPERATORS), OPERATORS)
    print(f"replay  : consistent={replay.consistent} integrity_ok={replay.integrity_ok}")

    assert result.succeeded and replay.consistent, "the wrapped agent should run and replay"
    print("\nOK — the existing agent runs unchanged, now governed + replayable.")


if __name__ == "__main__":
    main()
