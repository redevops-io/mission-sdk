"""`rdo mission ci` — the promotion gate.

Wraps the runtime's mission-CI: one pass/fail report over five checks — **feasibility** (compiles under
the grants), **budget** (simulated spend within budget), **run** (drives to a terminal state,
auto-approving the declared gates), **regression** (the final world contains the golden outcomes), and
**replay** (a fresh runtime rehydrating the same event log reconstructs the same terminal state). The
runtime's report type is mapped to an SDK type so no internal class crosses the boundary.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ._bootstrap import ensure_runtime
from ._compile import build_registry, register_program_template

ensure_runtime()

from agentic_os.mission.executor import Executor  # noqa: E402
from agentic_os.mission.mission_ci import run_mission_ci  # noqa: E402
from agentic_os.mission.operator_sdk import LocalOperatorClient  # noqa: E402
from agentic_os.mission.runtime import MissionRuntime  # noqa: E402


@dataclass
class CIResult:
    template: str
    passed: bool
    checks: list[tuple[str, bool, str]] = field(default_factory=list)

    def to_text(self) -> str:
        lines = [f"ci: {'PASS' if self.passed else 'FAIL'}  ({self.template})"]
        for name, ok, detail in self.checks:
            lines.append(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail and not ok else ""))
        return "\n".join(lines)


def _gate_capabilities(operators, program) -> list[str]:
    """Capability names the runtime will gate — matching the compiler, which gates on EITHER the
    capability's `approval_required` OR a step constraint mentioning human/review. `ci` must know both,
    or its `run` check parks on an un-approved gate."""
    names = {c.name for op in operators for c in op.manifest.capabilities if c.approval_required}
    provider = {prov: c.name for op in operators for c in op.manifest.capabilities for prov in c.provides}
    for st in program.steps:
        if any("human" in x.lower() or "review" in x.lower() for x in st.constraints):
            if st.outcome in provider:
                names.add(provider[st.outcome])
    return sorted(names)


def mission_ci(program, operators, *, golden: dict | None = None) -> CIResult:
    def factory(store):
        return MissionRuntime(
            build_registry(operators),
            Executor(LocalOperatorClient({op.name: op for op in operators})),
            store=store,
        )

    register_program_template(program)   # plan from the program's own steps, whatever its source
    report = run_mission_ci(
        factory, goal=program.goal, template=program.name, grants=list(program.grants),
        approve=_gate_capabilities(operators, program), golden=golden,
    )
    return CIResult(template=report.template, passed=report.passed,
                    checks=[(c.name, c.passed, c.detail) for c in report.checks])
