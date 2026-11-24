"""M2: bundle export, replay consistency, diff, verify — across all three dogfood fixtures."""
from __future__ import annotations

import importlib.util
import os

from redevops_mission import (
    diff_bundles, explain, export_bundle, replay_bundle, validate, verify_bundle,
)
from redevops_mission.bundle import CaseBundle

HERE = os.path.dirname(os.path.abspath(__file__))
EXAMPLES = os.path.join(HERE, os.pardir, "examples")


def _load(name):
    path = os.path.join(EXAMPLES, name, "mission.py")
    spec = importlib.util.spec_from_file_location(f"_ex_{name}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_deploy_release_fixture_validates():
    m = _load("deploy_release")
    assert validate(m.PROGRAM, m.OPERATORS).passed
    ex = explain(m.PROGRAM, m.OPERATORS)
    publish = next(n for n in ex.nodes if n["produces"] == "release_published")
    assert publish["approval"] and publish["undo"] == "release.yank"


def test_bundle_export_and_integrity():
    m = _load("deploy_release")
    b = export_bundle(m.PROGRAM, m.OPERATORS)      # auto-approves the publish gate
    assert b.state == "succeeded"
    assert b.integrity_ok()
    assert b.timeline().count("NodeSucceeded") == 4
    # json round-trip preserves integrity
    assert CaseBundle.from_json(b.to_json()).integrity_ok()


def test_replay_is_consistent():
    m = _load("deploy_release")
    b = export_bundle(m.PROGRAM, m.OPERATORS)
    r = replay_bundle(b, m.OPERATORS)
    assert r.consistent and r.integrity_ok
    assert r.recorded_state == r.replayed_state == "succeeded"


def test_replay_detects_tamper():
    m = _load("deploy_release")
    b = export_bundle(m.PROGRAM, m.OPERATORS)
    b.events.append({"seq": 999, "type": "Forged", "payload": {}})   # tamper after digest
    r = replay_bundle(b, m.OPERATORS)
    assert not r.integrity_ok and not r.consistent


def test_verify_reports_success_and_integrity():
    m = _load("dataops_reconcile")
    vr = verify_bundle(export_bundle(m.PROGRAM, m.OPERATORS))
    assert vr.succeeded and vr.integrity_ok
    assert vr.nodes_succeeded == 4


def test_diff_success_vs_parked():
    m = _load("revenue_rescue")
    done = export_bundle(m.PROGRAM, m.OPERATORS, approve=True)     # succeeds
    parked = export_bundle(m.PROGRAM, m.OPERATORS, approve=False)  # parks at the gate
    d = diff_bundles(done, parked)
    assert d["state"] == {"a": "succeeded", "b": "waiting_human"}
    assert "event_count" in d and "outcome_world" in d


def test_diff_identical_is_empty():
    m = _load("dataops_reconcile")
    a = export_bundle(m.PROGRAM, m.OPERATORS)
    b = export_bundle(m.PROGRAM, m.OPERATORS)
    # same deterministic mission → same state, timeline shape, and outcome world
    d = diff_bundles(a, b)
    assert "state" not in d and "outcome_world" not in d


# ---- what the seal has to catch -----------------------------------------------------------------------
# A bundle is read by someone who did not watch the run. Each test changes ONE thing in an exported bundle and expects verify and replay to refuse it.

def _gated_bundle():
    """The governed quickstart with the approval NOT given: the run stops at the gate, nothing was sent."""
    import runpy
    from pathlib import Path
    ns = runpy.run_path(str(Path(__file__).resolve().parents[1] / "examples" / "02_governed_quickstart" / "main.py"), run_name="not_main")
    return export_bundle(ns["PROGRAM"], ns["OPERATORS"], approve=False), ns["OPERATORS"]


def _edited(bundle, **changes):
    import json
    doc = json.loads(bundle.to_json())
    doc.update(changes)
    return CaseBundle.from_json(json.dumps(doc))


def test_a_run_that_stopped_at_the_gate_cannot_be_relabelled_as_succeeded():
    bundle, operators = _gated_bundle()
    assert bundle.state == "waiting_human" and not verify_bundle(bundle).succeeded
    forged = _edited(bundle, state="succeeded", outcome={"success": True, "world": {"sent": True}})
    report = verify_bundle(forged)
    assert not report.integrity_ok and not report.succeeded and "FAIL" in report.to_text()
    assert not replay_bundle(forged, operators).consistent


def test_each_sealed_field_is_under_the_digest():
    bundle, _ = _gated_bundle()
    assert bundle.integrity_ok() and bundle.digest.startswith("sha256:") and len(bundle.digest) == 71
    for field, value in (("goal", "something else"), ("outcome", {"success": True}), ("steps", []), ("origin", {"by": "someone"}),
                         ("source", "agent:other"), ("program", "other"), ("mission_id", "mission_x")):
        assert not _edited(bundle, **{field: value}).integrity_ok(), f"{field} can be changed without the digest noticing"
    events = [dict(e) for e in bundle.events][:-1]
    assert not _edited(bundle, events=events).integrity_ok()


def test_a_round_trip_through_json_keeps_the_digest_valid():
    bundle, _ = _gated_bundle()
    assert CaseBundle.from_json(bundle.to_json()).integrity_ok()


def test_an_older_bundle_still_loads_and_its_edited_state_is_caught_by_the_event_log():
    import json
    from redevops_mission.bundle import _digest_events
    bundle, _ = _gated_bundle()
    doc = json.loads(bundle.to_json())
    doc.update(schema_version="0.1", digest=_digest_events(doc["events"]))
    old = CaseBundle.from_json(json.dumps(doc))
    assert old.integrity_ok() and "events only" in verify_bundle(old).to_text()
    doc["state"] = "succeeded"                                   # 0.1 did not seal the state: the event log still contradicts it
    report = verify_bundle(CaseBundle.from_json(json.dumps(doc)))
    assert not report.succeeded and not report.integrity_ok
    del doc["schema_version"]                                    # a bundle that names no schema is read as 0.1, never as the current one
    assert CaseBundle.from_json(json.dumps(doc)).schema_version == "0.1"


def test_a_bundle_without_a_digest_is_not_intact():
    bundle, _ = _gated_bundle()
    assert not _edited(bundle, digest="").integrity_ok()
