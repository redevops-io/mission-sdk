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


def build_registry(operators):
    """A CapabilityRegistry with every authored operator's manifest registered."""
    registry = CapabilityRegistry()
    for op in operators:
        registry.register(op.manifest)
    return registry


def build_intent_from_program(program, mission_id: str) -> ExecutionIntent:
    return ExecutionIntent(
        mission_id=mission_id,
        rationale=f"{program.name} program",
        steps=[
            IntentStep(outcome=s.outcome, need=s.need, inputs_from=list(s.after),
                       constraints=list(s.constraints), value_hint=s.value)
            for s in program.steps
        ],
    )


def register_program_template(program) -> None:
    """Register the program's steps as the runtime template it plans from, so a `MissionProgram` runs
    regardless of whether a `@template` was declared. This is what makes the compilation path the same
    for a hand-authored mission and a `from_proposal` one (Discovery / a domain compiler): the runtime
    always plans from the program's own steps."""
    from agentic_os.mission.templates import TEMPLATES

    def factory(mission_id, _program=program):
        return build_intent_from_program(_program, mission_id)

    TEMPLATES[program.name] = factory


def compile_program(program, operators):
    """Return (mission, intent, plan, registry). Raises `CompileError` on an unbindable need, a missing
    grant, or a cyclic graph — the exact checks `rdo mission validate` reports."""
    registry = build_registry(operators)
    mission = Mission(goal=program.goal, policy_refs=list(program.grants))
    intent = build_intent_from_program(program, mission.id)
    plan = compile_intent(mission, intent, registry)
    return mission, intent, plan, registry
