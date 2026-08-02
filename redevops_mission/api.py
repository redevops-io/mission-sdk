"""`validate` and `explain` — the two read-only verbs of M0 (no execution).

`validate` runs static structural checks plus the runtime's deterministic compile (need→capability
binding, grant enforcement, acyclicity). `explain` renders the compiled physical graph. Both take a
public `MissionProgram` + the authored capabilities; neither runs anything or calls a model.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ._compile import CompileError, compile_program
from ._topology import topology


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
        _, _, plan, _ = compile_program(program, operators)
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
    _, _, plan, _ = compile_program(program, operators)
    produces_of = {n.id: (n.produces or n.capability) for n in plan.graph.nodes}
    nodes = [
        dict(id=n.id, capability=n.capability, produces=n.produces or n.capability,
             approval=n.approval_required, side_effect=n.side_effecting, undo=n.undo,
             depends_on=[produces_of.get(d, d) for d in n.depends_on])
        for n in plan.graph.nodes
    ]
    return Explanation(goal=program.goal, nodes=nodes)


@dataclass
class SimReport:
    expected_usd: float
    expected_success: float
    expected_latency_ms: int
    expected_approvals: int
    within_budget: bool
    notes: list[str] = field(default_factory=list)

    def to_text(self) -> str:
        lines = [
            "simulate: (dry-run — no execution, no model calls)",
            f"  expected cost      ${self.expected_usd}",
            f"  expected success   {self.expected_success}",
            f"  critical-path latency  {self.expected_latency_ms} ms",
            f"  human approvals    {self.expected_approvals}",
            f"  within budget      {self.within_budget}",
        ]
        for n in self.notes:
            lines.append(f"  ⚠ {n}")
        return "\n".join(lines)


def simulate(program, operators) -> SimReport:
    """Project cost / success / latency / approvals from capability metadata — no side effects."""
    from agentic_os.mission.simulator import simulate as _simulate

    mission, _, plan, registry = compile_program(program, operators)
    r = _simulate(plan, mission, registry)
    return SimReport(
        expected_usd=r.expected_usd, expected_success=r.expected_success,
        expected_latency_ms=r.expected_latency_ms, expected_approvals=r.expected_approvals,
        within_budget=r.within_budget, notes=list(r.notes),
    )


@dataclass
class ProfileReport:
    goal: str
    topo: dict = field(default_factory=dict)
    sim: SimReport | None = None

    def to_text(self) -> str:
        t = self.topo
        lines = [
            f"profile: {self.goal!r}   (EXPLAIN ANALYZE — static, no execution)",
            f"  nodes / edges         {t['nodes']} / {t['edges']}",
            f"  critical-path depth   {t['critical_path_depth']}",
            f"  max parallelism       {t['max_parallelism']}",
            f"  merge points          {t['merge_points']}",
            f"  human gates           {t['human_gates']}",
            f"  side effects          {t['side_effecting']}  (undo-covered {t['undo_covered']}/{t['side_effecting']})",
        ]
        if self.sim:
            lines += [
                f"  est. cost / latency   ${self.sim.expected_usd} / {self.sim.expected_latency_ms} ms",
                f"  est. success          {self.sim.expected_success}",
                f"  within budget         {self.sim.within_budget}",
            ]
        return "\n".join(lines)


def profile(program, operators) -> ProfileReport:
    """EXPLAIN ANALYZE for a mission: topology + projected cost/latency/success, all from the compiled
    plan and capability metadata (no execution)."""
    _, _, plan, _ = compile_program(program, operators)
    return ProfileReport(goal=program.goal, topo=topology(plan), sim=simulate(program, operators))
