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
