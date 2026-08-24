"""The v0.3.x runtime security plane, exercised through ONLY the public SDK.

A mission authored with declared capability security metadata (data_classifications / network /
required_authority) runs on the local profile with `secure=True`; the SDK wires the boundary
SecurityMonitor, correlates the trajectory into a disposition, drives containment, and surfaces the
Mission-native trace tree — none of which the author has to report by hand. A series of individually
permissible calls (read PII, then egress externally) correlates to DENY.
"""
from __future__ import annotations

from redevops_mission import MissionProgram, Operator, capability, run_program, step, template


@template("exfil_shape")
def exfil_shape(mission_id):
    return [
        step("records_read", need="read the customer records"),
        step("uploaded", need="upload the report to external storage", after=["records_read"]),
    ]


OPERATORS = [
    Operator("data", [
        capability("crm.read", handler=lambda i: {"records": 2000},
                   provides=["records_read"], permissions=["crm:read"],
                   required_authority=["read:crm"], data_classifications=["pii"]),
        capability("storage.upload", handler=lambda i: {},
                   provides=["uploaded"], permissions=["storage:write"], side_effecting=True,
                   undo="storage.delete", required_authority=["write:storage"],
                   network=["s3.external.com"]),
    ]),
]

PROGRAM = MissionProgram.from_template(
    "exfil_shape", goal="Read customer records and upload a report",
    grants=["crm:read", "storage:write"])


def test_insecure_run_has_no_security_assessment():
    r = run_program(PROGRAM, OPERATORS)                      # secure=False (default)
    assert r.succeeded
    assert r.disposition is None and r.spans == []          # nothing wired, nothing surfaced


def test_secure_run_correlates_pii_read_then_egress_to_deny():
    r = run_program(PROGRAM, OPERATORS, secure=True)
    assert r.succeeded                                       # each call was individually permissible
    assert r.disposition == "DENY"                          # the SERIES is an exfiltration shape
    assert r.containment == "CONTAINED"                     # DENY drives containment
    assert any("exfiltration" in reason for reason in r.security_reasons)
    # boundary telemetry the author never reported: the pii read + external egress are on the record
    assert r.spans, "a secure run surfaces the Mission-native trace tree"
    assert {s["trace_id"] for s in r.spans} == {r.spans[0]["trace_id"]}   # one causal tree
    upload = next(s for s in r.spans if s["name"] == "storage.upload")
    assert upload["attributes"]["redevops.network"] == ["s3.external.com"]


def test_delegated_authority_refuses_a_capability_beyond_the_lease():
    # a leased authority that covers read:crm but NOT write:storage
    from runtime_contracts import AuthorityContext, PrincipalRef
    auth = AuthorityContext(authority_id="m", principal=PrincipalRef(id="svc:ad", kind="service"),
                            purpose="run", scope=("read:crm",))
    r = run_program(PROGRAM, OPERATORS, secure=True, authority=auth)
    # crm.read (read:crm) is covered and runs; storage.upload (write:storage) is refused before its side
    # effect, so the mission does not reach success.
    assert not r.succeeded
    assert r.nodes_succeeded >= 1                            # crm.read did run under the covered authority
