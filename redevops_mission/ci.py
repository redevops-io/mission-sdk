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
from ._compile import build_registry

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


def _gate_capabilities(operators) -> list[str]:
    return [c.name for op in operators for c in op.manifest.capabilities if c.approval_required]


def mission_ci(program, operators, *, golden: dict | None = None) -> CIResult:
    def factory(store):
        return MissionRuntime(
            build_registry(operators),
            Executor(LocalOperatorClient({op.name: op for op in operators})),
            store=store,
        )

    report = run_mission_ci(
        factory, goal=program.goal, template=program.name, grants=list(program.grants),
        approve=_gate_capabilities(operators), golden=golden,
    )
    return CIResult(template=report.template, passed=report.passed,
                    checks=[(c.name, c.passed, c.detail) for c in report.checks])
