"""Discovery → one compilation path (design §13.3).

A Discovery Runtime proposal (a `suggested_template` + goal + a score/hypothesis) compiles to a
`MissionProgram` via `from_discovery` and then validates / runs / gates **identically** to a
hand-authored mission — carrying the proposal as `origin` (the "why"). Decoupled: the SDK consumes a
proposal-shaped dict, never the enterprise Discovery type. (An end-to-end run against the real
`DiscoveryRuntime` lives in the enterprise repo; this proves the boundary contract.)"""
from __future__ import annotations

from redevops_mission import (
    MissionProgram, Operator, capability, export_bundle, mission_ci, step, template, validate,
)


# a template a Discovery proposal can reference (in the runtime, built-ins like revenue_rescue are here)
@template("incident_response")
def incident_response(mission_id):
    return [
        step("incident_triaged", need="triage the incident and classify severity"),
        step("mitigation_applied", need="apply the mitigation", after=["incident_triaged"],
             constraints=["consequential — requires human approval"]),
        step("postmortem_filed", need="file the postmortem record", after=["mitigation_applied"]),
    ]


OPERATORS = [
    Operator("sre", [
        capability("sre.triage", handler=lambda i: {"sev": 2}, provides=["incident_triaged"],
                   permissions=["ops:read"]),
        capability("sre.mitigate", handler=lambda i: {"applied": True}, provides=["mitigation_applied"],
                   side_effecting=True, approval_required=True, undo="sre.rollback",
                   permissions=["ops:write"]),
        capability("sre.postmortem", handler=lambda i: {"doc": "pm_1"}, provides=["postmortem_filed"],
                   permissions=["docs:write"]),
    ]),
]
GRANTS = ["ops:read", "ops:write", "docs:write"]

# the shape a Discovery Runtime proposal serializes to (agentic_os/discovery/proposals.py::MissionProposal)
DISCOVERY_PROPOSAL = {
    "id": "prop_abc123",
    "goal": "Respond to the service-degradation incident on checkout",
    "subject": "checkout-service",
    "opportunity_class": "service_degradation",
    "suggested_template": "incident_response",
    "score": 0.82, "priority": "high", "hypothesis_id": "hyp_9",
    "decision": "propose", "approval_policy": "human",
}


def test_discovery_proposal_is_on_the_one_compilation_path():
    program = MissionProgram.from_discovery(DISCOVERY_PROPOSAL, grants=GRANTS)
    assert program.source == "discovery"
    assert program.name == "incident_response"
    # provenance: the proposal is recorded as the "why"
    assert program.origin["kind"] == "discovery:proposal"
    assert program.origin["ref"] == "prop_abc123"
    assert program.origin["opportunity_class"] == "service_degradation"

    # ...and it is now identical to a hand-authored mission on every verb
    assert validate(program, OPERATORS).passed
    assert mission_ci(program, OPERATORS).passed
    bundle = export_bundle(program, OPERATORS)          # auto-approves the mitigation gate
    assert bundle.state == "succeeded"
    assert bundle.origin["ref"] == "prop_abc123"        # the trigger travels into the audit record
    assert bundle.source == "discovery"


def test_discovery_and_human_produce_the_same_graph():
    """The only difference between a discovered mission and a hand-authored one is provenance."""
    from redevops_mission import explain

    discovered = MissionProgram.from_discovery(DISCOVERY_PROPOSAL, grants=GRANTS)
    hand = MissionProgram.from_template("incident_response", goal="x", grants=GRANTS)
    de = {(n["produces"], tuple(n["depends_on"])) for n in explain(discovered, OPERATORS).nodes}
    he = {(n["produces"], tuple(n["depends_on"])) for n in explain(hand, OPERATORS).nodes}
    assert de == he                                     # same graph
    assert discovered.source == "discovery" and hand.source == "human:template"
