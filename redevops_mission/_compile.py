"""Internal: lower a public `MissionProgram` to the runtime's compile path.

This is the single seam that reaches below the boundary: it rebuilds the internal `ExecutionIntent`
from the public `MissionProgram`, registers the authored capabilities, and calls the runtime's
deterministic `compile_intent` — which binds each need to a capability, enforces permissions against
the grants (fail-closed), and asserts the graph is acyclic. No LLM, no execution.
"""
from __future__ import annotations

from ._bootstrap import ensure_runtime

ensure_runtime()

from agentic_os.mission.compiler import CompileError, compile_intent  # noqa: E402,F401
from agentic_os.mission.registry import CapabilityRegistry  # noqa: E402
from agentic_os.mission.types import ExecutionIntent, IntentStep, Mission  # noqa: E402


def compile_program(program, operators):
    """Return (mission, intent, plan). Raises `CompileError` on an unbindable need, a missing grant,
    or a cyclic graph — the exact checks `rdo mission validate` reports."""
    registry = CapabilityRegistry()
    for op in operators:
        registry.register(op.manifest)

    mission = Mission(goal=program.goal, policy_refs=list(program.grants))
    intent = ExecutionIntent(
        mission_id=mission.id,
        rationale=f"{program.name} program",
        steps=[
            IntentStep(outcome=s.outcome, need=s.need, inputs_from=list(s.after),
                       constraints=list(s.constraints), value_hint=s.value)
            for s in program.steps
        ],
    )
    plan = compile_intent(mission, intent, registry)
    return mission, intent, plan
