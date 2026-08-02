"""M0 acceptance: Revenue Rescue authored through only the SDK boundary validates and explains,
and the negative cases (missing grant, unbindable outcome, cycle) are reported, not crashed."""
from __future__ import annotations

import importlib.util
import os

from redevops_mission import MissionProgram, explain, validate

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURE = os.path.join(HERE, os.pardir, "examples", "revenue_rescue", "mission.py")


def _load():
    spec = importlib.util.spec_from_file_location("_rr", FIXTURE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_validate_passes():
    m = _load()
    report = validate(m.PROGRAM, m.OPERATORS)
    assert report.passed, report.to_text()
    assert report.nodes == 4


def test_explain_renders_graph():
    m = _load()
    ex = explain(m.PROGRAM, m.OPERATORS)
    outcomes = {n["produces"] for n in ex.nodes}
    assert outcomes == {"dunning_attempted", "reply_drafted", "campaign_drafted", "reconciliation_staged"}
    # the money-moving step carries the human gate
    dunning = next(n for n in ex.nodes if n["produces"] == "dunning_attempted")
    assert dunning["approval"] is True and dunning["side_effect"] is True
    # the books step folds the two parallel branches back in
    recon = next(n for n in ex.nodes if n["produces"] == "reconciliation_staged")
    assert set(recon["depends_on"]) == {"reply_drafted", "campaign_drafted"}


def test_missing_grant_is_reported_not_raised():
    m = _load()
    stripped = MissionProgram.from_dict({**m.PROGRAM.to_dict(), "grants": ["support:write"]})
    report = validate(stripped, m.OPERATORS)
    assert not report.passed
    assert any("permission denied" in c.detail for c in report.checks)


def test_unknown_after_ref_is_reported():
    m = _load()
    d = m.PROGRAM.to_dict()
    d["steps"][1]["after"] = ["does_not_exist"]
    report = validate(MissionProgram.from_dict(d), m.OPERATORS)
    assert not report.passed
    assert any("unknown after-refs" in c.detail for c in report.checks)


def test_program_json_roundtrip():
    m = _load()
    rt = MissionProgram.from_json(m.PROGRAM.to_json())
    assert rt.to_dict() == m.PROGRAM.to_dict()
