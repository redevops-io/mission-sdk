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


def register_steps_template(name: str, steps: list[dict]) -> None:
    """Register a runtime template from plain step dicts (outcome/need/after/constraints/value). Used to
    plan from a program's own steps — and, crucially, to re-register on `replay` in a fresh process,
    where the runtime's `rehydrate` re-compiles the plan and needs the template present."""
    from agentic_os.mission.templates import TEMPLATES

    def factory(mission_id, _steps=steps, _name=name):
        return ExecutionIntent(
            mission_id=mission_id, rationale=f"{_name} program",
            steps=[
                IntentStep(outcome=s["outcome"], need=s["need"], inputs_from=list(s.get("after", [])),
                           constraints=list(s.get("constraints", [])), value_hint=s.get("value", "medium"))
                for s in _steps
            ],
        )

    TEMPLATES[name] = factory


def program_step_dicts(program) -> list[dict]:
    return [{"outcome": s.outcome, "need": s.need, "after": s.after,
             "constraints": s.constraints, "value": s.value} for s in program.steps]


def register_program_template(program) -> None:
    """Register the program's steps as the runtime template it plans from, so a `MissionProgram` runs
    regardless of whether a `@template` was declared — the same compilation path for a hand-authored
    mission and a `from_proposal` one (Discovery / a domain compiler)."""
    register_steps_template(program.name, program_step_dicts(program))


def compile_program(program, operators):
    """Return (mission, intent, plan, registry). Raises `CompileError` on an unbindable need, a missing
    grant, or a cyclic graph — the exact checks `rdo mission validate` reports."""
    registry = build_registry(operators)
    mission = Mission(goal=program.goal, policy_refs=list(program.grants))
    intent = build_intent_from_program(program, mission.id)
    plan = compile_intent(mission, intent, registry)
    return mission, intent, plan, registry
