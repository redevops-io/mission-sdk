"""A mission parked on a human gate survives a restart: a later runtime resumes it from a durable store."""
from __future__ import annotations

from redevops_mission import (
    MissionProgram, MissionStep, Operator, capability, open_event_store, pending_tasks, resume_program,
)
from redevops_mission.profiles import drive

PROGRAM = MissionProgram(name="durable_resume_fixture", goal="answer a question", grants=["sim:write"], steps=[
    MissionStep("question_asked", "ask"),
    MissionStep("answer_collected", "collect the answer", after=["question_asked"]),
    MissionStep("answer_applied", "apply", after=["answer_collected"]),
])


def _operators(calls: list) -> list:
    return [Operator("fixture", [
        capability("q.ask", handler=lambda i: calls.append("ask") or {"q": "2+2?"}, provides=["question_asked"]),
        capability("q.collect", provides=["answer_collected"], approval_required=True,
                   handler=lambda i: calls.append("collect") or {"a": (i.get("_approval") or {}).get("a")}),
        capability("q.apply", provides=["answer_applied"], side_effecting=True, permissions=["sim:write"],
                   handler=lambda i: calls.append("apply") or {"ok": i["answer_collected"]["a"] == "4"}),
    ])]


def test_parked_mission_resumes_in_a_fresh_runtime(tmp_path):
    path = str(tmp_path / "ledger.ndjson")
    first: list = []
    _, mid, m, _ = drive(PROGRAM, _operators(first), store=open_event_store("jsonl", path=path))
    assert m.state.value == "waiting_human" and first == ["ask"]

    later: list = []                                     # "after a restart": new operators, new store handle
    rt, m2 = resume_program(PROGRAM, _operators(later), mid, store=open_event_store("jsonl", path=path))
    assert m2.state.value == "waiting_human" and later == []        # folded, not re-executed
    (task,) = pending_tasks(rt, mid)
    done = rt.approve(mid, task["node_id"], "approve", edit={"a": "4"})
    assert done.state.value == "succeeded" and later == ["collect", "apply"]
    assert done.outcome["world"]["answer_applied"] == {"ok": True}
