"""`validate` and `explain` — the two read-only verbs of M0 (no execution).

`validate` runs static structural checks plus the runtime's deterministic compile (need→capability
binding, grant enforcement, acyclicity). `explain` renders the compiled physical graph. Both take a
public `MissionProgram` + the authored capabilities; neither runs anything or calls a model.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ._compile import CompileError, compile_program


@dataclass
class Check:
    name: str
    ok: bool
    detail: str = ""


@dataclass
class ValidateReport:
    passed: bool
    checks: list[Check] = field(default_factory=list)
    nodes: int = 0

    def to_text(self) -> str:
        lines = [f"validate: {self.name_line()}"]
        for c in self.checks:
            mark = "PASS" if c.ok else "FAIL"
            lines.append(f"  [{mark}] {c.name}" + (f" — {c.detail}" if c.detail else ""))
        return "\n".join(lines)

    def name_line(self) -> str:
        return "OK" if self.passed else "FAILED"


def validate(program, operators) -> ValidateReport:
    checks: list[Check] = []
    outcomes = [s.outcome for s in program.steps]

    checks.append(Check("has steps", bool(program.steps),
                        "" if program.steps else "the program declares no steps"))

    dupes = sorted({o for o in outcomes if outcomes.count(o) > 1})
    checks.append(Check("outcomes are unique", not dupes,
                        "" if not dupes else f"duplicated: {dupes}"))

    declared = set(outcomes)
    bad = [(s.outcome, a) for s in program.steps for a in s.after if a not in declared]
    checks.append(Check("dependencies resolve to declared outcomes", not bad,
                        "" if not bad else f"unknown after-refs: {bad}"))

    nodes = 0
    try:
        _, _, plan = compile_program(program, operators)
        nodes = len(plan.graph.nodes)
        checks.append(Check(
            "compiles (needs bind to capabilities · grants cover permissions · graph acyclic)",
            True, f"{nodes} nodes"))
    except CompileError as e:
        checks.append(Check(
            "compiles (needs bind to capabilities · grants cover permissions · graph acyclic)",
            False, str(e)))

    return ValidateReport(passed=all(c.ok for c in checks), checks=checks, nodes=nodes)


@dataclass
class Explanation:
    goal: str
    nodes: list[dict] = field(default_factory=list)

    def to_text(self) -> str:
        lines = [f"explain: {self.goal!r}", f"  {len(self.nodes)} nodes"]
        for n in self.nodes:
            tags = []
            if n["approval"]:
                tags.append("human-gate")
            if n["side_effect"]:
                tags.append("side-effect" + (f"→undo:{n['undo']}" if n.get("undo") else ""))
            dep = f"  ⟵ {', '.join(n['depends_on'])}" if n["depends_on"] else ""
            tagstr = f"  [{' · '.join(tags)}]" if tags else ""
            lines.append(f"  • {n['produces']}  ({n['capability']}){tagstr}{dep}")
        return "\n".join(lines)


def explain(program, operators) -> Explanation:
    """Compile the program and render the physical graph. Raises `CompileError` if it does not compile
    (run `validate` first for a full report rather than a single error)."""
    _, _, plan = compile_program(program, operators)
    produces_of = {n.id: (n.produces or n.capability) for n in plan.graph.nodes}
    nodes = [
        dict(id=n.id, capability=n.capability, produces=n.produces or n.capability,
             approval=n.approval_required, side_effect=n.side_effecting, undo=n.undo,
             depends_on=[produces_of.get(d, d) for d in n.depends_on])
        for n in plan.graph.nodes
    ]
    return Explanation(goal=program.goal, nodes=nodes)
