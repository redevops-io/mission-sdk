"""Concurrency guards for the safe-parallel scheduler.

Two things this suite locks down (per the parallel-execution remediation plan):

  1. **No silent ceiling divergence.** The effective per-wave concurrency is bounded by BOTH the executor
     pool AND the scheduler's release cap. The SDK exposes ONE user-facing control (`concurrency`) that must
     move both together, and the *effective* limit must be observable — so a pool of 8 quietly throttled to
     4 by policy can never recur unnoticed.
  2. **Actual overlap (CI guard, plan §36).** A barrier proves independent nodes really run concurrently —
     a happens-before assertion, not a flaky latency threshold — so a regression back to serial execution
     fails loudly.
"""
from __future__ import annotations

import threading

from redevops_mission import MissionProgram, Operator, capability, run_program, step, template


def _two_independent(handlers):
    """A mission with two independent (dependency-free) nodes → one ready wave."""
    name = f"conc_{id(handlers)}"

    @template(name)
    def _t(mission_id):
        return [step("a_done", need="node a"), step("b_done", need="node b")]

    ops = [Operator("w", [
        capability("cap.a", handler=handlers[0], provides=["a_done"]),
        capability("cap.b", handler=handlers[1], provides=["b_done"]),
    ])]
    return MissionProgram.from_template(name, goal="concurrency guard", grants=[]), ops


# ── 1. single control + no silent divergence ──────────────────────────────────────────────────────────

def test_single_sdk_control_moves_both_ceilings_together():
    """run_program(concurrency=8) must NOT be silently throttled to the policy default (4): the SDK's one
    control sets both the executor pool and the scheduler release cap, so the effective limit == 8."""
    prog, ops = _two_independent([lambda i: {"a": 1}, lambda i: {"b": 1}])
    r = run_program(prog, ops, concurrency=8)
    assert r.succeeded
    assert r.effective_concurrency == 8, f"effective concurrency throttled to {r.effective_concurrency}"
    assert r.scheduler_policy == "safe_parallel"


def test_serial_is_the_default_and_is_labelled():
    prog, ops = _two_independent([lambda i: {"a": 1}, lambda i: {"b": 1}])
    r = run_program(prog, ops)   # no concurrency arg
    assert r.effective_concurrency == 1
    assert r.scheduler_policy == "serial"


def test_effective_concurrency_reports_the_binding_limit_when_ceilings_diverge():
    """Direct-construct the runtime with mismatched ceilings (pool 8, policy 4). The effective limit is
    OBSERVABLE as the binding minimum (4) — divergence is surfaced, never hidden behind the larger number."""
    from agentic_os.mission.runtime import MissionRuntime
    from agentic_os.mission.scheduler import SchedulePolicy

    from redevops_mission.authoring import Operator as _Op  # noqa: F401 - ensure package import path
    from redevops_mission.profiles import build_registry
    from redevops_mission.profiles import LocalOperatorClient, LocalEventLedger
    from agentic_os.mission.executor import Executor

    _, ops = _two_independent([lambda i: {"a": 1}, lambda i: {"b": 1}])
    registry = build_registry(ops)
    rt = MissionRuntime(registry, Executor(LocalOperatorClient({o.name: o for o in ops})),
                        store=LocalEventLedger(None).store(),
                        max_concurrency=8, policy=SchedulePolicy(max_concurrency=4))
    assert rt.effective_max_concurrency == 4   # min(8, 4) — the divergence is visible, not masked


# ── 2. barrier overlap guard (plan §36) ───────────────────────────────────────────────────────────────

def test_independent_nodes_actually_overlap_under_concurrency():
    """Barrier proof of concurrency: node A waits (bounded) for node B to signal it has started. Under
    real overlap A sees B's signal; under serial execution A runs alone and times out. Deterministic —
    no latency threshold."""
    started_b = threading.Event()
    saw = {"a_saw_b": None}

    def a(_i):
        saw["a_saw_b"] = started_b.wait(timeout=2.0)   # True only if B ran concurrently
        return {"a": 1}

    def b(_i):
        started_b.set()
        return {"b": 1}

    prog, ops = _two_independent([a, b])
    r = run_program(prog, ops, concurrency=2)
    assert r.succeeded
    assert saw["a_saw_b"] is True, "independent nodes did NOT overlap — scheduler regressed to serial"


def test_serial_mode_does_not_overlap():
    """The compatibility/debug path: concurrency=1 runs strictly serially, so A never sees B start."""
    started_b = threading.Event()
    saw = {"a_saw_b": None}

    def a(_i):
        saw["a_saw_b"] = started_b.wait(timeout=0.3)
        return {"a": 1}

    def b(_i):
        started_b.set()
        return {"b": 1}

    prog, ops = _two_independent([a, b])
    r = run_program(prog, ops, concurrency=1)
    assert r.succeeded
    assert saw["a_saw_b"] is False, "serial mode overlapped — the two ceilings may have diverged"
