"""DataOpsBench S21 — cross-source reconciliation-conflict detection, as a mission (dogfood #2).

The mission form of the S21 task (see redevops-io/DataOpsBench): operate a platform with an acquired
source (Northstar + Meridian) and surface every reconciliation conflict the merge introduces. It is
authored through **only** the public SDK surface, and it stresses a different shape than Revenue Rescue
— two parallel per-source extractions feeding a governed `merge()`, then a `verify()` gate — mapping
onto the Spark boundary rule (per-source extraction on executors, the cross-source union on the driver).

No human gate, no side effects: this exercises the SDK's read/compute mission path end to end.

    rdo mission validate examples/dataops_reconcile/mission.py
    rdo mission profile  examples/dataops_reconcile/mission.py
    rdo mission run       examples/dataops_reconcile/mission.py
"""
from __future__ import annotations

from redevops_mission import MissionProgram, Operator, capability, step, template


@template("dataops_reconcile")
def dataops_reconcile(mission_id):
    return [
        step("northstar_extracted",
             need="extract keyed revenue metrics from the Northstar source"),
        step("meridian_extracted",
             need="extract keyed revenue metrics from the acquired Meridian source"),
        step("conflicts_detected",
             need="detect cross-source reconciliation conflicts via governed merge()",
             after=["northstar_extracted", "meridian_extracted"]),
        step("reconciliation_verified",
             need="verify every seeded cross-source conflict was surfaced (recall/precision)",
             after=["conflicts_detected"],
             constraints=["must pass the deterministic reconciliation gate"]),
    ]


OPERATORS = [
    Operator("dataops-extract", [
        capability("extract.northstar", handler=lambda i: {"metrics": {"cm_0": "1200 USD"}},
                   provides=["northstar_extracted"], permissions=["dataops:read"]),
        capability("extract.meridian", handler=lambda i: {"metrics": {"cm_0": "1080 EUR"}},
                   provides=["meridian_extracted"], permissions=["dataops:read"]),
    ]),
    Operator("dataops-merge", [
        capability("merge.detect_conflicts", handler=lambda i: {"conflicts": ["cm_0"]},
                   provides=["conflicts_detected"], permissions=["dataops:merge"]),
    ]),
    Operator("dataops-verify", [
        capability("verify.reconciliation", handler=lambda i: {"recall": 1.0, "precision": 1.0},
                   provides=["reconciliation_verified"], permissions=["dataops:verify"]),
    ]),
]

GRANTS = ["dataops:read", "dataops:merge", "dataops:verify"]

PROGRAM = MissionProgram.from_template(
    "dataops_reconcile", goal="Detect every cross-source reconciliation conflict", grants=GRANTS,
)
